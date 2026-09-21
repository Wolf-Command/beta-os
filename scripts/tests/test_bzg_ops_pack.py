#!/usr/bin/env python3
"""BZG ops pack — Devi phone loop on a temp catalog. Beta only.

Create → submit → ops approve → partial receive → close, petty, issue,
stock honesty. Payment execution stays refused. CAP-BZG-03 is not rewritten.
CR-215a379980f228e8 stays OPEN. No PROVEN or READY.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)

from core import audit  # noqa: E402
from core import evidence  # noqa: E402
from core import uma_devi_p0 as p0  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402
from core import venue_close  # noqa: E402
from core import work_items  # noqa: E402

PASS = 0
FAIL = 0
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
CR_ID = "CR-215a379980f228e8"
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py":
        "a8e89d399bd33ec11135b8caaa002a0d18c70000b6a8972d46811d30a61c9881",
    "scripts/phase26_team.py":
        "7c3690afaea97d8fdb48422bf4cbc8e144c9ecfac45c24c19977e83d45088fe0",
    "scripts/skills/__init__.py":
        "edfb69ce6d8f92a88ee6bf6a8160d9926765843271961bba52a3754450c93105",
    "scripts/wolf_intelligence.py":
        "e1de6a248512bcdaf6e71c4db30dc80a229055c7707e682c73d9349acb9bc21b",
}
MUTATIONS = (
    "/api/bzg/uma-blu/receive",
    "/api/bzg/uma-blu/prs",
    "/api/bzg/uma-blu/issues",
    "/api/bzg/uma-blu/petty",
    "/api/bzg/uma-blu/pay",
)


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


def cr_state() -> str:
    conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT state FROM wolf_completion_items WHERE id=?",
            (CR_ID,),
        ).fetchone()
        return str(row[0]) if row else ""
    finally:
        conn.close()


def patch(path: Path) -> None:
    ops.CATALOG_DB = path
    evidence.CATALOG_DB = path
    audit.CATALOG_DB = path
    venue_close.CATALOG_DB = path
    work_items.CATALOG_DB = path


def anon_matrix() -> None:
    import serve_beta as sb

    handler = sb.BetaHandler
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        for path in MUTATIONS:
            req = Request(
                base + path,
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(req, timeout=8) as resp:
                    check(f"anon POST {path} 403", False, f"status {resp.status}")
            except HTTPError as exc:
                check(f"anon POST {path} 403", exc.code == 403, str(exc.code))
        req = Request(base + "/api/bzg/uma-blu/today", method="GET")
        try:
            with urlopen(req, timeout=8) as resp:
                check("anon GET today 403", False, f"status {resp.status}")
        except HTTPError as exc:
            check("anon GET today 403", exc.code == 403, str(exc.code))
    finally:
        httpd.shutdown()


def main() -> int:
    for rel, digest in WIP.items():
        check(f"WIP unchanged {Path(rel).name}", sha(ROOT / rel) == digest)
    assessments = json.loads((ROOT / "state" / "model-c-baseline-assessments.json").read_text(encoding="utf-8"))
    check("CAP-BZG-03 stays READY", assessments.get("CAP-BZG-03", [None])[0] == "READY")
    check("ledger stays 77", len(assessments) == 77)
    check("open BZG-03 CR stays OPEN before", cr_state() == "OPEN")
    src = (SCRIPTS / "core" / "uma_devi_p0.py").read_text(encoding="utf-8")
    check("no PERS-DEVI hard-code", '== "PERS-DEVI"' not in src and "== 'PERS-DEVI'" not in src)
    today_html = (ROOT / "dashboards" / "bzg-uma-blu.html").read_text(encoding="utf-8")
    check("phone today width", "max-width: 480px" in today_html)
    check("stock honesty on today", "not a live inventory count" in today_html)
    pr_html = (ROOT / "dashboards" / "bzg-uma-blu-pr.html").read_text(encoding="utf-8")
    check("no payment button", "Approve payment" not in pr_html and "Execute payment" not in pr_html)
    check("evidence slot on receive", "evidence_note_id" in pr_html)

    td = Path(tempfile.mkdtemp(prefix="bzg-ops-pack-", dir=str(ROOT / "state")))
    db = td / "content_library.sqlite"
    try:
        shutil.copy2(LIVE_DB, db)
        patch(db)
        conn = ops.db_connect(db)
        try:
            pr = ops.create_pr(
                supplier_name="Morning market",
                purpose="Greens for service",
                lines=[{"item": "Kangkung", "qty": 4, "unit": "bunch"}],
                submitted=False,
                verified_person_id="PERS-DEVI",
                actor_type="PERSON",
                conn=conn,
            )
            check("draft created", pr["state"] == "DRAFT", pr["state"])
            submitted = p0.ops_advance(
                person_id="PERS-DEVI",
                pr_id=pr["pr_id"],
                to_state="REQUESTED",
                conn=conn,
            )
            check("submitted", submitted["state"] == "REQUESTED", submitted["state"])
            approved = p0.ops_advance(
                person_id="PERS-DEVI",
                pr_id=pr["pr_id"],
                to_state="APPROVED",
                conn=conn,
            )
            check("ops approved", approved["state"] == "APPROVED", approved["state"])
            ordered = p0.ops_advance(
                person_id="PERS-DEVI",
                pr_id=pr["pr_id"],
                to_state="ORDERED",
                conn=conn,
            )
            check("ordered", ordered["state"] == "ORDERED")
            try:
                p0.ops_advance(
                    person_id="PERS-DEVI",
                    pr_id=pr["pr_id"],
                    to_state="PAYMENT_APPROVED",
                    conn=conn,
                )
                check("payment execution refused", False, "advance returned")
            except ops.UmaOpsError as exc:
                check("payment execution refused", exc.code == "payment_execution_refused", exc.code)

            detail = p0.pr_detail(pr["pr_id"], conn=conn)
            line_id = detail["lines"][0]["source_line_id"]
            try:
                p0.receive_goods(
                    person_id="PERS-DEVI",
                    pr_key=pr["pr_id"],
                    lines=[{"source_line_id": line_id, "received_qty": 1}],
                    require_evidence=True,
                    conn=conn,
                )
                check("receive requires evidence", False, "accepted without evidence")
            except ops.UmaOpsError as exc:
                check("receive requires evidence", exc.code == "missing_evidence", exc.code)

            partial = p0.receive_goods(
                person_id="PERS-DEVI",
                pr_key=pr["pr_id"],
                lines=[{"source_line_id": line_id, "received_qty": 1}],
                evidence_note_id="NOTE-PACK-1",
                require_evidence=True,
                conn=conn,
            )
            check("partial receipt", partial["status"] == "PARTIAL", partial["status"])
            check("variance flag", partial["variance_flag"] is True)
            check("variance is not a stock count", partial["variance_is_not_a_stock_count"] is True)
            check("alchemist not verified", partial["wolf_verified_alchemist"] is False)
            mid = ops.get_pr(pr["pr_id"], conn=conn)
            check("state partially received", mid["state"] == "PARTIALLY_RECEIVED", mid["state"])

            stock = ops.stock_framework(conn=conn)
            check("on hand empty", stock["on_hand"] is None and stock["on_hand_status"] == "EMPTY")
            check("empty is not live inventory", stock["empty_is_not_live_inventory"] is True)
            check("not perpetual", stock["live_perpetual_inventory"] is False)
            check("esb not mutated", stock["esb_mutated"] is False)
            check("variance hook present", len(stock["variance_hooks"]) == 1)
            check("stock not proven", stock["proven"] is False and stock["ready"] is False)

            done = p0.receive_goods(
                person_id="PERS-DEVI",
                pr_key=pr["pr_id"],
                lines=[{"source_line_id": line_id, "received_qty": 3}],
                evidence_photo_id="PHOTO-PACK-1",
                require_evidence=True,
                conn=conn,
            )
            check("complete receipt", done["status"] == "COMPLETE" and done["variance_flag"] is False, done["status"])
            full = ops.get_pr(pr["pr_id"], conn=conn)
            check("state received", full["state"] == "RECEIVED", full["state"])
            closed = p0.ops_advance(
                person_id="PERS-DEVI",
                pr_id=pr["pr_id"],
                to_state="OPS_CLOSED",
                evidence_note_id="NOTE-CLOSE-1",
                conn=conn,
            )
            check("ops closed", closed["state"] == "OPS_CLOSED", closed["state"])
            check("close did not execute payment", closed.get("payment_execution") is False)

            petty = ops.record_petty_ops(
                person_id="PERS-DEVI",
                direction="OUT",
                amount=15000,
                purpose="Ice for service",
                conn=conn,
            )
            check("petty recorded", petty.get("direction") == "OUT" and petty.get("example") is False)

            issue = ops.create_operator_issue(
                person_id="PERS-DEVI",
                source_kind="close_exception",
                note="Delivery was short this morning",
                source_id=pr["pr_id"],
                conn=conn,
            )
            check("issue opened", issue["status"] == "OPEN" and issue["cr_resolved"] is False)
            issues = ops.list_issues(conn=conn)
            check(
                "issue listed",
                any(row.get("issue_id") == issue["issue_id"] for row in issues["issues"]),
            )

            today = ops.today_cards(conn=conn, person_id="PERS-DEVI")
            check("today ok", today.get("ok") is True)
            check("today stock empty honesty", (today.get("stock") or {}).get("empty_is_not_live_inventory") is True)
            check("today payment off", today.get("payment_execution") is False)
            perm = today.get("permissions") or {}
            check("devi operator view", perm.get("view") == "operator")
            buttons = perm.get("buttons") or {}
            check("devi can receive", buttons.get("receive") is True)
            check("devi can perform close", buttons.get("perform_close") is True)
            check("devi payment button hidden", buttons.get("payment_execution") is False)
            check("devi progress hidden", buttons.get("progress") is False)
            owner = p0.operator_view("PERS-MATT", conn=conn)
            check("owner manager read", owner.get("view") == "owner" and owner.get("manager_read") is True)
            check("owner has no money controls", owner.get("sees_money_controls") is False)
            check(
                "owner payment hidden",
                (owner.get("buttons") or {}).get("payment_execution") is False,
            )
            flags = ops.honesty_flags()
            check("honesty not proven", flags.get("proven") is False and flags.get("ready") is False)
            check("human commissioning not done", flags.get("human_commissioning") == "NOT_DONE")
        finally:
            conn.close()
    finally:
        shutil.rmtree(td, ignore_errors=True)
        patch(LIVE_DB)

    check("open BZG-03 CR stays OPEN after", cr_state() == "OPEN")
    anon_matrix()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAIL")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
