#!/usr/bin/env python3
"""GGV Content Machine ops depth — library detail/action + Needs-You / Owner refresh."""
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

from core import ggv_content_ops_depth as pack  # noqa: E402
from core import request_auth as ra  # noqa: E402

PASS = 0
FAIL = 0

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CR_01 = pack.CR_01
CR_05 = pack.CR_05
MATT = "mrwolf@wolfcommand.net"
AMANDA = "amanda@wolfcommand.net"
HAIKAL = "haikalqilbari123@gmail.com"
MISA_EMAIL = "mlsary111@gmail.com"
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


def _first_asset_id(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT id FROM assets ORDER BY id ASC LIMIT 1").fetchone()
    if not row:
        raise RuntimeError("no assets in catalog copy")
    return int(row[0])


def test_honesty() -> None:
    flags = pack.honesty_flags()
    check("bound", flags.get("bound") == "beta-ggv-loop-safe")
    check(
        "operator depth schema",
        flags.get("operator_depth_schema_id") == pack.OPERATOR_DEPTH_SCHEMA_ID,
    )
    check("empty operator honesty", flags.get("empty_operator_is_not_invent") is True)
    check("no invent proven", flags.get("proven") is False and flags.get("invented_proven") is False)
    check("no invent ready", flags.get("ready") is False and flags.get("invented_ready") is False)
    check("no invent staff_ready", flags.get("staff_ready") is False)
    check("no haikal human invent", flags.get("invented_haikal_human_pass") is False)
    check("no metricool publish", flags.get("metricool_publish") is False)
    check("no klaviyo publish", flags.get("klaviyo_publish") is False)
    check("no nas destroy", flags.get("nas_destroy") is False)
    check("cr not resolved", flags.get("cr_resolved") is False)
    schema = pack.schema_document()
    check(
        "operator depth in schema",
        schema.get("operator_depth_schema_id") == pack.OPERATOR_DEPTH_SCHEMA_ID,
    )
    check(
        "action kinds",
        schema.get("content_operator_action_kinds")
        == sorted(pack.CONTENT_OPERATOR_ACTION_KINDS),
    )
    for fn, code in (
        (pack.refuse_proven, "proven_refused"),
        (pack.refuse_ready, "ready_refused"),
        (pack.refuse_staff_ready, "staff_ready_refused"),
        (pack.refuse_haikal_human, "haikal_human_refused"),
        (pack.refuse_metricool, "metricool_refused"),
        (pack.refuse_klaviyo, "klaviyo_refused"),
        (pack.refuse_nas_destroy, "nas_destroy_refused"),
        (pack.refuse_invent_asset, "invent_asset_refused"),
        (pack.refuse_production, "production_refused"),
    ):
        try:
            fn({})
            check(f"{code} raises", False)
        except pack.ContentOpsError as exc:
            check(f"{code}", exc.code == code, exc.code)
    check(
        "refuse_code skips operator-action",
        pack.refuse_code("/api/content/ops-depth/objects/X/operator-action") is None,
    )
    check(
        "refuse_code skips operator-depth",
        pack.refuse_code("/api/content/ops-depth/operator-depth") is None,
    )
    check(
        "refuse_code still refuses metricool",
        pack.refuse_code("/api/content/ops-depth/metricool") == "metricool",
    )


def test_operator_depth_on_copy(td: Path) -> None:
    db = td / "catalog.sqlite"
    op_db = td / "operator.sqlite"
    shutil.copy2(LIVE_DB, db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        grant = pack.ensure_operator_depth_rbac(conn=conn, commit=True)
        check(
            "rbac grant ok",
            grant.get("ok") is True
            and pack.PERM_CONTENT_OPERATOR in (grant.get("grants") or []),
            str(grant)[:200],
        )
        for pid in ("PERS-AMANDA", "PERS-HAIKAL", "PERS-MISA", "PERS-MATT"):
            prove = pack.prove_content_operator(person_id=pid, conn=conn)
            check(
                f"{pid} content operator",
                prove.get("can_content_operator") is True
                and prove.get("assignment_active") is True
                and prove.get("live_habitat_commission") is False
                and prove.get("actions", {}).get("metricool_publish") is False
                and prove.get("actions", {}).get("klaviyo_publish") is False
                and prove.get("actions", {}).get("nas_destroy") is False
                and prove.get("actions", {}).get("handoff_touch") is True,
                str(prove)[:240],
            )

        desk = pack.operator_depth_desk(
            verified_person_id="PERS-HAIKAL",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator depth desk",
            desk.get("ok") is True
            and desk.get("bound") == "beta-ggv-loop-safe"
            and desk.get("schema_id") == pack.OPERATOR_DEPTH_SCHEMA_ID
            and len(desk.get("object_candidates") or []) >= 1
            and desk.get("metricool_publish") is False
            and desk.get("staff_ready") is False
            and (desk.get("owner_attention") or {}).get("empty") is True
            and desk.get("haikal_human_status") == "not_started",
            str(desk)[:280],
        )
        check(
            "nas readiness strip",
            isinstance(desk.get("nas_readiness"), dict)
            and desk["nas_readiness"].get("staff_ready") is False
            and desk["nas_readiness"].get("invented_haikal_human_pass") is False,
        )

        asset_id = _first_asset_id(conn)
        oid = pack.object_id_for_asset(asset_id)
        detail = pack.operator_object_detail(
            oid,
            verified_person_id="PERS-HAIKAL",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator library detail",
            detail.get("ok") is True
            and detail.get("bound") == "beta-ggv-loop-safe"
            and bool(detail.get("actions", {}).get("content_operator"))
            and detail.get("metricool_publish") is False
            and detail.get("nas_destroy") is False
            and "/content-2.0#content-obj-" in str(detail.get("href") or ""),
            str(detail.get("actions"))[:200],
        )

        note = pack.record_content_operator_action(
            verified_person_id="PERS-HAIKAL",
            object_id=oid,
            kind="note",
            note="Content depth note — library fixture only.",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator note",
            note.get("ok") is True
            and note.get("kind") == "note"
            and note.get("metricool_publish") is False
            and note.get("staff_ready") is False
            and (note.get("owner_attention") or {}).get("empty") is False,
            str(note)[:240],
        )

        tag = pack.record_content_operator_action(
            verified_person_id="PERS-HAIKAL",
            object_id=oid,
            kind="tag-touch",
            note="pool-wide, habitat-fixture",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator tag_touch",
            tag.get("ok") is True
            and tag.get("kind") == "tag_touch"
            and "pool-wide" in ((tag.get("object") or {}).get("tags") or []),
            str((tag.get("object") or {}).get("tags")),
        )

        nxt = pack.record_content_operator_action(
            verified_person_id="PERS-AMANDA",
            object_id=oid,
            kind="next-action-touch",
            note="Prep cut for Habitat reel — no publish.",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator next_action alias",
            nxt.get("ok") is True
            and nxt.get("kind") == "next_action"
            and (nxt.get("object") or {}).get("recorded_next_action")
            == "Prep cut for Habitat reel — no publish."
            and (nxt.get("content_desk_needs_you") or {}).get("empty") is False,
            str(nxt.get("object"))[:200],
        )

        ho = pack.record_content_operator_action(
            verified_person_id="PERS-MISA",
            object_id=oid,
            kind="handoff-touch",
            note="Handoff library review to Owner — still staff_ready=false.",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator handoff",
            ho.get("ok") is True
            and ho.get("kind") == "handoff_touch"
            and (ho.get("owner_attention") or {}).get("empty") is False
            and any(
                "handoff_touch" in (i.get("reasons") or [])
                for i in ((ho.get("owner_attention") or {}).get("items") or [])
            ),
            str(ho.get("owner_attention"))[:200],
        )

        # Second asset for dismiss (if only one asset, reuse after re-open not needed)
        ids = pack.list_library_asset_ids(conn=conn, limit=5)
        dismiss_id = ids[1] if len(ids) > 1 else ids[0]
        dismiss_oid = pack.object_id_for_asset(dismiss_id)
        if dismiss_oid == oid and len(ids) == 1:
            # single-asset catalog: dismiss the same object after proving handoff
            pass
        dismiss = pack.record_content_operator_action(
            verified_person_id="PERS-MATT",
            object_id=dismiss_oid,
            kind="dismiss-noise",
            note="Dismissed noise — no Metricool publish.",
            catalog_db=db,
            operator_db=op_db,
        )
        check(
            "operator dismiss",
            dismiss.get("ok") is True
            and dismiss.get("kind") == "dismiss_noise"
            and (dismiss.get("object") or {}).get("dismissed") is True,
        )
        desk2 = pack.operator_depth_desk(
            verified_person_id="PERS-HAIKAL",
            catalog_db=db,
            operator_db=op_db,
        )
        cand_ids = [c.get("object_id") for c in (desk2.get("object_candidates") or [])]
        check(
            "dismiss drops candidate",
            dismiss_oid not in cand_ids,
            str(cand_ids[:8]),
        )

        try:
            pack.record_content_operator_action(
                verified_person_id="PERS-HAIKAL",
                object_id=oid,
                kind="metricool-publish",
                note="no",
                catalog_db=db,
                operator_db=op_db,
            )
            check("invalid metricool kind refused", False)
        except pack.ContentOpsError as exc:
            check("invalid metricool kind refused", exc.code == "invalid_kind", exc.code)

        try:
            pack.operator_object_detail(
                "asset-999999",
                verified_person_id="PERS-HAIKAL",
                catalog_db=db,
                operator_db=op_db,
            )
            check("missing asset not invent", False)
        except pack.ContentOpsError as exc:
            check("missing asset not invent", exc.code == "not_found", exc.code)

        check(f"cr {CR_01} still open on copy", _cr(CR_01, db) == "OPEN")
        check(f"cr {CR_05} still open on copy", _cr(CR_05, db) == "OPEN")
    finally:
        conn.close()


def test_static_and_caps() -> None:
    serve = (ROOT / "scripts" / "serve_beta.py").read_text(encoding="utf-8")
    for needle in (
        "_ggv_content_ops_operator_depth",
        "_ggv_content_ops_operator_depth_rbac",
        "_ggv_content_ops_object_operator_detail",
        "_ggv_content_ops_object_operator_action",
        "/api/content/ops-depth",
        "objects/([^/]+)/operator-action",
    ):
        check(f"route {needle}", needle in serve)
    page = (ROOT / "dashboards" / "content-2.0.html").read_text(encoding="utf-8")
    check("page operator depth", "Operator depth" in page)
    check("page content-ops-depth", "content-ops-depth" in page)
    check("page operator-action", "operator-action" in page)
    check(
        "page no metricool publish CTA",
        "No Metricool/Klaviyo publish" in page,
    )
    before = {rel: sha(ROOT / rel) for rel in WIP}
    for rel, digest in before.items():
        WIP[rel] = digest
        check(f"wip present {Path(rel).name}", (ROOT / rel).is_file())
    ledger = _ledger()
    check("CAP-GGV-01 built", ledger.get("CAP-GGV-01", [None])[0] == "BUILT")
    check("CAP-GGV-05 built", ledger.get("CAP-GGV-05", [None])[0] == "BUILT")
    check("CAP-GGV-03 specified", ledger.get("CAP-GGV-03", [None])[0] == "SPECIFIED")
    check("CAP-GGV-06 specified", ledger.get("CAP-GGV-06", [None])[0] == "SPECIFIED")
    check(f"live {CR_01} open", _cr(CR_01) == "OPEN")
    check(f"live {CR_05} open", _cr(CR_05) == "OPEN")
    check("denominator 77", len(ledger) == 77)


def test_api() -> None:
    ra._ENV_LOADED = True
    import serve_beta as sb
    from core.canonical_guard import isolate_runtime_catalog
    isolate_runtime_catalog()
    pack.ensure_operator_depth_rbac(commit=True)

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
            ("/api/content/ops-depth/operator-depth", "depth", "GET"),
            ("/api/content/ops-depth/rbac", "rbac", "GET"),
            ("/content-2.0", "page", "GET"),
            (
                "/api/content/ops-depth/objects/asset-1/operator-action",
                "action",
                "POST",
            ),
        ):
            st, _ = call(method, path, None, {} if method == "POST" else None)
            check(f"anon {label} 403", st == 403, str(st))

        st, depth = call("GET", "/api/content/ops-depth/operator-depth", HAIKAL)
        check(
            "haikal operator-depth 200",
            st == 200
            and isinstance(depth, dict)
            and depth.get("ok") is True
            and depth.get("bound") == "beta-ggv-loop-safe"
            and depth.get("staff_ready") is False
            and (depth.get("rbac") or {}).get("can_content_operator") is True,
            str(depth)[:240] if isinstance(depth, dict) else str(st),
        )
        st, rbac = call("GET", "/api/content/ops-depth/rbac", HAIKAL)
        check(
            "haikal rbac prove",
            st == 200
            and isinstance(rbac, dict)
            and rbac.get("can_content_operator") is True
            and rbac.get("actions", {}).get("metricool_publish") is False,
            str(rbac)[:200] if isinstance(rbac, dict) else str(st),
        )
        st, detail = call(
            "GET",
            "/api/content/ops-depth/objects/asset-1/operator",
            HAIKAL,
        )
        check(
            "haikal library operator detail",
            st == 200
            and isinstance(detail, dict)
            and detail.get("ok") is True
            and detail.get("metricool_publish") is False
            and detail.get("staff_ready") is False,
            str(detail)[:200] if isinstance(detail, dict) else str(st),
        )
        st, blank = call(
            "POST",
            "/api/content/ops-depth/objects/asset-1/operator-action",
            HAIKAL,
            {"kind": "note", "note": ""},
        )
        check(
            "haikal note validates",
            st in (400, 403) and isinstance(blank, dict),
            f"{st} {str(blank)[:120]}",
        )
        st, refused = call(
            "POST",
            "/api/content/ops-depth/objects/asset-1/operator-action",
            HAIKAL,
            {"kind": "note", "note": "x", "metricool_publish": True},
        )
        check(
            "haikal metricool body refused",
            st in (403, 405) and isinstance(refused, dict),
            f"{st} {str(refused)[:120]}",
        )
        st, _anon_act = call(
            "POST",
            "/api/content/ops-depth/objects/asset-1/operator-action",
            None,
            {"kind": "note", "note": "anon"},
        )
        check("anon operator-action 403", st == 403, str(st))
        st, _out = call("GET", "/api/content/ops-depth/operator-depth", OUTSIDER)
        check("outsider depth 403", st == 403, str(st))
        st, amanda = call("GET", "/api/content/ops-depth/operator-depth", AMANDA)
        check(
            "amanda depth 200",
            st == 200 and isinstance(amanda, dict) and amanda.get("ok") is True,
            str(st),
        )
        st, misa = call("GET", "/api/content/ops-depth/operator-depth", MISA_EMAIL)
        check(
            "misa depth 200",
            st == 200 and isinstance(misa, dict) and misa.get("ok") is True,
            str(st),
        )
        st, matt = call("GET", "/api/content/ops-depth/operator-depth", MATT)
        check(
            "matt depth 200",
            st == 200 and isinstance(matt, dict) and matt.get("ok") is True,
            str(st),
        )
        st, page = call("GET", "/content-2.0", HAIKAL)
        check(
            "haikal page 200",
            st == 200 and isinstance(page, (bytes, str)),
            str(st),
        )
        if isinstance(page, bytes):
            text = page.decode("utf-8", "replace")
        else:
            text = str(page)
        check(
            "haikal page hides operator depth chrome",
            "Operator depth" not in text and "CONTENT PLAN" in text,
        )
    finally:
        httpd.shutdown()
        httpd.server_close()

    after = {rel: sha(ROOT / rel) for rel in WIP}
    for rel, digest in WIP.items():
        check(f"wip untouched {Path(rel).name}", after.get(rel) == digest)


def main() -> int:
    test_honesty()
    with tempfile.TemporaryDirectory(prefix="ggv-content-ops-") as tmp:
        test_operator_depth_on_copy(Path(tmp))
    test_static_and_caps()
    test_api()
    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
