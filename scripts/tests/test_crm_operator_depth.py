#!/usr/bin/env python3
"""Sprint2 P8 CRM Lead Operator Depth — lead detail/action + consequence refresh."""
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

from core import crm_mgmt_cluster as crm  # noqa: E402
from core import lead_spine as spine  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CR_ID = "CR-ff42f3a7c49caa79"
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA_EMAIL = "misa@wolfcommand.net"
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


def test_honesty() -> None:
    flags = crm.honesty_flags()
    check("bound", flags.get("bound") == "beta-ggv-loop-safe")
    check(
        "operator depth schema",
        flags.get("operator_depth_schema_id") == crm.OPERATOR_DEPTH_SCHEMA_ID,
    )
    check("no live habitat commission", flags.get("live_habitat_commission") is False)
    check("empty leads honesty", flags.get("empty_leads_is_not_invent") is True)
    check("no invent proven", flags.get("proven") is False and flags.get("invented_proven") is False)
    check("no invent ready", flags.get("ready") is False and flags.get("invented_ready") is False)
    check("cr not resolved", flags.get("cr_resolved") is False)
    schema = crm.schema_document()
    check(
        "operator depth in schema",
        schema.get("operator_depth_schema_id") == crm.OPERATOR_DEPTH_SCHEMA_ID,
    )
    check(
        "action kinds",
        schema.get("crm_operator_action_kinds") == sorted(crm.CRM_OPERATOR_ACTION_KINDS),
    )
    for fn, code in (
        (crm.refuse_proven, "proven_refused"),
        (crm.refuse_ready, "ready_refused"),
        (crm.refuse_production, "production_refused"),
        (crm.refuse_crm_write, "crm_write_refused"),
        (crm.refuse_klaviyo_send, "klaviyo_send_refused"),
        (crm.refuse_money, "money_refused"),
    ):
        try:
            fn({})
            check(f"{code} raises", False)
        except crm.MgmtClusterError as exc:
            check(f"{code}", exc.code == code, exc.code)
    check(
        "refuse_code skips operator-action",
        crm.refuse_code("/api/crm/mgmt-cluster/leads/X/operator-action") is None,
    )
    check(
        "refuse_code skips operator-depth",
        crm.refuse_code("/api/crm/mgmt-cluster/operator-depth") is None,
    )


def test_operator_depth_on_copy(td: Path) -> None:
    db = td / "catalog.sqlite"
    shutil.copy2(LIVE_DB, db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        grant = crm.ensure_operator_depth_rbac(conn=conn, commit=True)
        check(
            "rbac grant ok",
            grant.get("ok") is True and crm.PERM_CRM_OPERATOR in (grant.get("grants") or []),
            str(grant)[:200],
        )
        for pid in ("PERS-AMANDA", "PERS-HAIKAL", "PERS-MISA"):
            prove = crm.prove_crm_operator(person_id=pid, conn=conn)
            check(
                f"{pid} crm operator",
                prove.get("can_crm_operator") is True
                and prove.get("assignment_active") is True
                and prove.get("live_habitat_commission") is False
                and prove.get("actions", {}).get("crm_write") is False
                and prove.get("actions", {}).get("handover_touch") is True,
                str(prove)[:240],
            )

        lead_id = _lead_id(conn, "demo-01")
        detail = crm.operator_lead_detail(
            lead_id,
            verified_person_id="PERS-AMANDA",
            conn=conn,
        )
        check(
            "operator lead detail",
            detail.get("ok") is True
            and detail.get("bound") == "beta-ggv-loop-safe"
            and bool(detail.get("actions", {}).get("crm_operator"))
            and detail.get("external_crm_write") is False
            and detail.get("invented_leads") is False
            and "/crm-mgmt-cluster#crm-lead-" in str(detail.get("href") or ""),
            str(detail.get("actions"))[:200],
        )

        note = crm.record_crm_lead_operator_action(
            verified_person_id="PERS-AMANDA",
            lead_id=lead_id,
            kind="note",
            note="CRM depth note — Habitat fixture only.",
            conn=conn,
        )
        check(
            "operator note",
            note.get("ok") is True
            and note.get("kind") == "note"
            and note.get("external_crm_write") is False
            and note.get("lead_spine", {}).get("invented_leads") is False,
        )

        nxt = crm.record_crm_lead_operator_action(
            verified_person_id="PERS-AMANDA",
            lead_id=lead_id,
            kind="next-action-touch",
            note="Call Habitat contact with CRM outline.",
            conn=conn,
        )
        check(
            "operator next_action alias",
            nxt.get("ok") is True
            and nxt.get("kind") == "next_action"
            and nxt["lead"].get("recorded_next_action") == "Call Habitat contact with CRM outline.",
            str((nxt.get("lead") or {}).get("recorded_next_action")),
        )
        check(
            "ggv desk consequence refreshed",
            isinstance(nxt.get("ggv_desk_next_action"), dict)
            and nxt["ggv_desk_next_action"].get("invented_leads") is False,
        )
        check(
            "owner attention present",
            isinstance(nxt.get("owner_attention"), dict)
            and nxt["owner_attention"].get("invented") is False,
        )
        check(
            "staff attention present",
            isinstance(nxt.get("staff_attention"), dict)
            and nxt["staff_attention"].get("invented") is False,
        )

        touch = crm.record_crm_lead_operator_action(
            verified_person_id="PERS-HAIKAL",
            lead_id=lead_id,
            kind="ownership_touch",
            note="Haikal CRM ownership touch.",
            conn=conn,
        )
        check(
            "ownership touch",
            touch.get("ok") is True
            and touch.get("kind") == "ownership_touch"
            and touch.get("external_crm_write") is False,
        )

        hand = crm.record_crm_lead_operator_action(
            verified_person_id="PERS-AMANDA",
            lead_id=lead_id,
            kind="handover_touch",
            note="Handover to content seat — fixture only.",
            conn=conn,
        )
        check(
            "handover touch",
            hand.get("ok") is True
            and hand.get("kind") == "handover_touch"
            and (hand.get("owner_attention", {}).get("count") or 0) >= 1,
            str(hand.get("owner_attention"))[:200],
        )

        # Separate fixture for dismiss so demo-01 stays in spine for other asserts.
        lead2 = _lead_id(conn, "demo-02")
        dismiss = crm.record_crm_lead_operator_action(
            verified_person_id="PERS-MISA",
            lead_id=lead2,
            kind="dismiss_noise",
            note="Noise — not a real CRM lead action needed.",
            conn=conn,
        )
        check(
            "dismiss noise",
            dismiss.get("ok") is True
            and dismiss.get("kind") == "dismiss_noise"
            and dismiss.get("external_crm_write") is False,
        )
        desk = crm.operator_depth_desk(verified_person_id="PERS-AMANDA", conn=conn)
        dismissed_ids = {r.get("lead_id") for r in (desk.get("lead_candidates") or [])}
        check(
            "dismiss drops candidate",
            lead2 not in dismissed_ids,
            str(sorted(dismissed_ids))[:200],
        )
        check(
            "operator depth desk",
            desk.get("ok") is True
            and desk.get("bound") == "beta-ggv-loop-safe"
            and desk.get("live_habitat_commission") is False
            and desk.get("rbac", {}).get("can_crm_operator") is True
            and desk.get("invented_leads") is False
            and desk.get("cr_resolved") is False,
        )

        try:
            crm.record_crm_lead_operator_action(
                verified_person_id="PERS-NOBODY",
                lead_id=lead_id,
                kind="note",
                note="outsider",
                conn=conn,
            )
            check("outsider refused", False)
        except crm.MgmtClusterError as exc:
            check("outsider refused", exc.code == "forbidden", exc.code)

        other = spine.ingest_observation(
            entity_id="ENT-BZG",
            brand_id="BZG-UMA",
            source_system="fixture",
            source_id="crm-depth-other-brand",
            source_observed_at="2026-09-22T02:00:00Z",
            source_stage="new",
            provenance={"demo": True, "label": "OTHER BRAND CRM DEPTH"},
            actor_type="SYSTEM",
            conn=conn,
        )
        other_id = other["lead"]["lead_id"]
        try:
            crm.record_crm_lead_operator_action(
                verified_person_id="PERS-AMANDA",
                lead_id=other_id,
                kind="note",
                note="Must not cross brands.",
                conn=conn,
            )
            check("cross brand refused", False)
        except crm.MgmtClusterError as exc:
            check("cross brand isolated", exc.code == "brand_isolated", exc.code)

        src = conn.execute(
            "SELECT source_stage FROM core_leads WHERE lead_id=?",
            (lead_id,),
        ).fetchone()[0]
        check("source stage held", src == "new")
        check("cr still open on copy", _cr(CR_ID, db) == "OPEN")
    finally:
        conn.close()


def test_sources() -> None:
    src = (SCRIPTS / "core" / "crm_mgmt_cluster.py").read_text(encoding="utf-8")
    check("operator depth schema in pack", crm.OPERATOR_DEPTH_SCHEMA_ID in src)
    check("operator_lead_detail fn", "def operator_lead_detail" in src)
    check("record_crm_lead_operator_action fn", "def record_crm_lead_operator_action" in src)
    check("ensure rbac fn", "def ensure_operator_depth_rbac" in src)
    check("lead spine consequence fn", "def lead_spine_consequence" in src)
    check("ggv desk consequence fn", "def ggv_desk_next_action_consequence" in src)
    check("owner attention fn", "def owner_attention_consequence" in src)
    check("staff attention fn", "def staff_attention_consequence" in src)
    check("no completion update", "UPDATE wolf_completion" not in src and "mark_resolved" not in src)
    check("no ledger dump", "json.dump(" not in src)
    spine_src = (SCRIPTS / "core" / "lead_spine.py").read_text(encoding="utf-8")
    check("handover event", "handover_touch_recorded" in spine_src)
    check("dismiss event", "dismiss_noise_recorded" in spine_src)
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    for needle in (
        "/api/crm/mgmt-cluster/operator-depth",
        "operator-action",
        "_crm_mgmt_operator_depth",
        "_crm_mgmt_lead_operator_detail",
        "_crm_mgmt_lead_operator_action",
    ):
        check(f"route {needle}", needle in serve)
    page = (ROOT / "dashboards" / "crm-mgmt-cluster.html").read_text(encoding="utf-8")
    check("page operator depth", "Operator depth" in page)
    check("page operator-action", "operator-action" in page)
    check("page no crm write", "External CRM not written" in page)
    before = {rel: sha(ROOT / rel) for rel in WIP}
    for rel, digest in before.items():
        WIP[rel] = digest
        check(f"wip present {Path(rel).name}", (ROOT / rel).is_file())
    ledger = _ledger()
    check("cap-crm-01 built", ledger.get("CAP-CRM-01", [None])[0] == "BUILT")
    check("cap-crm-02 specified", ledger.get("CAP-CRM-02", [None])[0] == "SPECIFIED")
    check("cap-crm-03 specified", ledger.get("CAP-CRM-03", [None])[0] == "SPECIFIED")
    check("cap-crm-04 built", ledger.get("CAP-CRM-04", [None])[0] == "BUILT")
    check("live cr open", _cr(CR_ID) == "OPEN")
    check("denominator 77", len(ledger) == 77)


def test_api() -> None:
    ra._ENV_LOADED = True
    os.environ["WOLF_ALLOW_LIVE_AUDIT"] = "1"
    try:
        crm.ensure_operator_depth_rbac(commit=True)
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

    live = sqlite3.connect(str(LIVE_DB))
    try:
        live_id = _lead_id(live, "demo-02")
        live_before = live.execute(
            "SELECT wolf_stage, owner_person_id, source_stage, first_human_touch_at FROM core_leads WHERE lead_id=?",
            (live_id,),
        ).fetchone()
        live_events = live.execute(
            "SELECT COUNT(*) FROM core_lead_events WHERE lead_id=?",
            (live_id,),
        ).fetchone()[0]
    finally:
        live.close()

    try:
        for path, label, method in (
            ("/api/crm/mgmt-cluster/operator-depth", "depth", "GET"),
            ("/api/crm/mgmt-cluster/operator-depth/rbac", "rbac", "GET"),
            ("/crm-mgmt-cluster", "page", "GET"),
            (f"/api/crm/mgmt-cluster/leads/{live_id}/operator-action", "action", "POST"),
        ):
            st, _ = call(method, path, None, {} if method == "POST" else None)
            check(f"anon {label} 403", st == 403, str(st))

        st, depth = call("GET", "/api/crm/mgmt-cluster/operator-depth", AMANDA)
        check(
            "amanda operator-depth 200",
            st == 200
            and isinstance(depth, dict)
            and depth.get("ok") is True
            and depth.get("bound") == "beta-ggv-loop-safe"
            and depth.get("live_habitat_commission") is False
            and (depth.get("rbac") or {}).get("can_crm_operator") is True,
            str(depth)[:240] if isinstance(depth, dict) else str(st),
        )
        st, rbac = call("GET", "/api/crm/mgmt-cluster/operator-depth/rbac", HAIKAL)
        check(
            "haikal rbac prove",
            st == 200
            and isinstance(rbac, dict)
            and rbac.get("can_crm_operator") is True
            and rbac.get("live_habitat_commission") is False,
            str(rbac)[:200] if isinstance(rbac, dict) else str(st),
        )
        st, detail = call(
            "GET", f"/api/crm/mgmt-cluster/leads/{live_id}/operator", AMANDA
        )
        check(
            "amanda lead operator detail",
            st == 200
            and isinstance(detail, dict)
            and detail.get("ok") is True
            and detail.get("external_crm_write") is False,
            str(detail)[:200] if isinstance(detail, dict) else str(st),
        )
        st, blank = call(
            "POST",
            f"/api/crm/mgmt-cluster/leads/{live_id}/operator-action",
            AMANDA,
            {"kind": "note", "note": ""},
        )
        check(
            "amanda note validates",
            st in (400, 403) and isinstance(blank, dict),
            f"{st} {str(blank)[:120]}",
        )
        st, _anon_act = call(
            "POST",
            f"/api/crm/mgmt-cluster/leads/{live_id}/operator-action",
            None,
            {"kind": "note", "note": "anon"},
        )
        check("anon operator-action 403", st == 403, str(st))
        st, _out = call("GET", "/api/crm/mgmt-cluster/operator-depth", OUTSIDER)
        check("outsider depth 403", st == 403, str(st))
        st, page = call("GET", "/crm-mgmt-cluster", AMANDA)
        check(
            "amanda page 200",
            st == 200 and isinstance(page, (dict, bytes, str)),
            str(st),
        )

        live2 = sqlite3.connect(str(LIVE_DB))
        try:
            after = live2.execute(
                "SELECT wolf_stage, owner_person_id, source_stage, first_human_touch_at FROM core_leads WHERE lead_id=?",
                (live_id,),
            ).fetchone()
            after_events = live2.execute(
                "SELECT COUNT(*) FROM core_lead_events WHERE lead_id=?",
                (live_id,),
            ).fetchone()[0]
        finally:
            live2.close()
        check("live lead unchanged by api prove", after == live_before, f"{after} vs {live_before}")
        check("live events unchanged by blank prove", after_events == live_events)
    finally:
        httpd.shutdown()
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
