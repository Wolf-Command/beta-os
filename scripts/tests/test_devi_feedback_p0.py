#!/usr/bin/env python3
"""Devi feedback P0 — close history, PR detail, append-only receive.

Beta only. Temp catalog. No Alchemist writes. No payment grant.
Full Uma commissioning stays NOT_DONE. Completion items are not resolved.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALCHEMIST_DB", None)

from core import audit as audit  # noqa: E402
from core import evidence as evidence  # noqa: E402
from core import uma_devi_p0 as p0  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402
from core import venue_close as venue_close  # noqa: E402

LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
PASS = 0
FAIL = 0

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


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def patch(path: Path) -> None:
    ops.CATALOG_DB = path
    evidence.CATALOG_DB = path
    audit.CATALOG_DB = path
    venue_close.CATALOG_DB = path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alchemist_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE pr_orders (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          pr_num TEXT,
          department TEXT,
          requested_by TEXT,
          vendor TEXT,
          order_date TEXT,
          status TEXT,
          notes TEXT,
          created_at TEXT,
          invoice_total REAL
        );
        CREATE TABLE pr_order_lines (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          pr_id INTEGER,
          item TEXT,
          qty REAL,
          unit TEXT,
          received_qty REAL,
          short_over TEXT,
          price REAL
        );
        CREATE TABLE cash_count (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          count_date TEXT,
          counted REAL,
          expected REAL
        );
        CREATE TABLE petty_cash (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          entry_date TEXT, flow TEXT, category TEXT, description TEXT,
          amount REAL, logged_by_name TEXT, created_at TEXT
        );
        CREATE TABLE ledger (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          amount REAL, payment_status TEXT, hold INTEGER DEFAULT 0
        );
        """
    )
    conn.execute(
        """
        INSERT INTO pr_orders
          (pr_num, department, requested_by, vendor, order_date, status, notes, created_at, invoice_total)
        VALUES ('PR-1422', 'Kitchen', 'Devi', 'Harbour Fish', '2026-09-01', 'Received',
                NULL, '2026-09-01T08:00:00+08:00', NULL)
        """
    )
    conn.execute(
        """
        INSERT INTO pr_order_lines (pr_id, item, qty, unit, received_qty, price)
        VALUES (1, 'Prawns', 10, 'kg', 0, NULL)
        """
    )
    conn.execute(
        "INSERT INTO cash_count (count_date, counted, expected) VALUES ('2026-09-01', 0, 0)"
    )
    conn.execute(
        """
        INSERT INTO petty_cash
          (entry_date, flow, category, description, amount, logged_by_name, created_at)
        VALUES ('2026-09-18', 'Cash Out (Spend)', 'Meal', 'Staff meal', 50000, 'Devi', '2026-09-18T12:00:00+08:00')
        """
    )
    conn.execute(
        """
        INSERT INTO ledger (amount, payment_status, hold) VALUES (1000, 'unpaid', 0)
        """
    )
    conn.commit()
    conn.close()


def grant_receive(conn: sqlite3.Connection) -> None:
    ts = "2026-09-19T00:00:00+08:00"
    conn.execute(
        """
        INSERT INTO org_permissions (
          permission_id, code, resource, action, description, status, created_at, updated_at
        ) VALUES (
          'PERM-VENUE-RECEIVE-TEST', 'venue.receive', 'venue', 'receive',
          'Test-only receive gate', 'ACTIVE', ?, ?
        )
        """,
        (ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_role_permissions (role_id, permission_id, effect, created_at, updated_at)
        VALUES ('ROLE-BZG-HFB', 'PERM-VENUE-RECEIVE-TEST', 'ALLOW', ?, ?)
        """,
        (ts, ts),
    )
    conn.commit()


def insert_close(conn: sqlite3.Connection, close_id: str, day: str, state: str) -> None:
    conn.execute(
        """
        INSERT INTO venue_daily_closes (
          close_id, entity_id, venue_brand_id, business_date, state,
          declared_cash_amount, declared_cash_evidence_id, variance_cash_amount,
          fingerprint_stale, submitted_by_person_id, created_at, updated_at
        ) VALUES (?, 'ENT-BZG', 'BZG-UMA', ?, ?, 125000, 'EVD-FIXTURE', 0, 0, 'PERS-DEVI', ?, ?)
        """,
        (close_id, day, state, f"{day}T10:00:00Z", f"{day}T10:00:00Z"),
    )


def main() -> int:
    src = (SCRIPTS / "core" / "uma_devi_p0.py").read_text(encoding="utf-8")
    mig = (SCRIPTS / "migrations" / "migrate_uma_devi_feedback_p0.py").read_text(encoding="utf-8")
    check("module does not resolve completion items", "mark_resolved" not in src)
    check("module does not grant payment approval", "INSERT INTO org_role_permissions" not in src)
    check("module does not query cash_count", "FROM cash_count" not in src and "JOIN cash_count" not in src)
    check("migration does not insert a payment grant", "bzg.pr.payment_approve" in mig and "INSERT INTO org_role_permissions" not in mig)
    for rel, digest in WIP.items():
        check(f"WIP unchanged {Path(rel).name}", sha(ROOT / rel) == digest)

    live = sqlite3.connect(str(LIVE_DB))
    hfb_pay = live.execute(
        """
        SELECT COUNT(*) FROM org_role_permissions rp
        JOIN org_permissions p ON p.permission_id = rp.permission_id
        WHERE rp.role_id='ROLE-BZG-HFB' AND p.code='bzg.pr.payment_approve'
        """
    ).fetchone()[0]
    live_receive = live.execute(
        "SELECT COUNT(*) FROM org_permissions WHERE code LIKE '%receive%'"
    ).fetchone()[0]
    resolved_before = live.execute(
        "SELECT COUNT(*) FROM wolf_completion_items WHERE state='RESOLVED'"
    ).fetchone()[0]
    live.close()
    check("live HFB has no payment_approve", hfb_pay == 0, str(hfb_pay))
    check("live RBAC has no receive permission", live_receive == 0, str(live_receive))

    close_html = (ROOT / "dashboards" / "uma-blu-close.html").read_text(encoding="utf-8")
    today_html = (ROOT / "dashboards" / "bzg-uma-blu.html").read_text(encoding="utf-8")
    pr_html = (ROOT / "dashboards" / "bzg-uma-blu-pr.html").read_text(encoding="utf-8")
    check("close page has Previous tab", "tabPrevious" in close_html and "Previous" in close_html)
    check("close empty copy is honest", p0.EMPTY_PREVIOUS in close_html)
    check("close submit buttons are capability-tagged", 'data-cap="submit"' in close_html)
    check("close page is mobile width", 'width=device-width' in close_html and "480px" in close_html)
    check("today renders waiting copy", "waiting_copy" in today_html and "actionable === false" in today_html)
    check("today page is mobile width", 'width=device-width' in today_html and "480px" in today_html)
    check("PR detail shows Existing chip", "Existing" in pr_html)
    check("PR detail has no payment approve button", "Approve payment" not in pr_html)
    check("PR detail is mobile width", 'width=device-width' in pr_html and "480px" in pr_html)

    td = tempfile.mkdtemp(prefix="devi-p0-", dir=str(ROOT / "state"))
    alc_path = Path(td) / "alchemist.db"
    try:
        db = Path(td) / "content_library.sqlite"
        shutil.copy2(LIVE_DB, db)
        patch(db)
        alchemist_db(alc_path)
        os.environ["WOLF_ALCHEMIST_DB"] = str(alc_path)
        before_hash = sha(alc_path)

        conn = ops.db_connect(db)
        resolved_copy = conn.execute(
            "SELECT COUNT(*) FROM wolf_completion_items WHERE state='RESOLVED'"
        ).fetchone()[0]
        check("copy resolved count matches live", resolved_copy == resolved_before)

        caps = p0.close_capabilities("PERS-DEVI", conn=conn)
        can = caps["can"]
        check("Devi cannot submit close", can["submit"] is False and can["open"] is False and can["reconcile"] is False)
        check("Devi is not granted payment approve", can["payment_approve"] is False)
        check("denied explanation names closer", "Waiting on closer" in (caps.get("denied_explanation") or ""))
        check("receive absent so Devi cannot receive yet", can["receive"] is False and caps.get("receive_permission") is None)

        empty = p0.previous_closes(conn=conn)
        check("previous empty message", empty["empty"] is True and empty["empty_message"] == p0.EMPTY_PREVIOUS)
        check("empty previous did not use cash_count", empty["alchemist_cash_count_used"] is False)
        check("cash_count zero was not turned into a close", empty["count"] == 0)

        insert_close(conn, "VDC-OLD", "2026-09-01", "OPEN")
        insert_close(conn, "VDC-NEW", "2026-09-02", "VERIFIED_CLOSED")
        conn.commit()
        audit.record_event(
            action="venue_close.verify",
            result="SUCCEEDED",
            source="venue_close",
            actor_type="PERSON",
            verified_person_id="PERS-DEVI",
            actor_person_id="PERS-DEVI",
            resource_type="venue_daily_close",
            resource_id="VDC-NEW",
            entity_id="ENT-BZG",
            brand_id="BZG-UMA",
            conn=conn,
            commit=True,
        )
        listed = p0.previous_closes(exclude_business_date="2026-09-19", conn=conn)
        dates = [row["business_date"] for row in listed["closes"]]
        check("previous newest first", dates == ["2026-09-02", "2026-09-01"], str(dates))
        newest = listed["closes"][0]
        check("verified chip only when stored state says so", newest.get("chip") == "Wolf-verified")
        check("declared cash comes from the close row", newest.get("declared_cash_amount") == 125000)
        check("older close is not Wolf-verified", listed["closes"][1].get("chip") is None)
        detail = p0.close_detail("VDC-NEW", conn=conn)
        check("detail has evidence ref", any(r["evidence_id"] == "EVD-FIXTURE" for r in detail["evidence_refs"]))
        check(
            "detail has audit sentence",
            any("Close verified" in (s.get("sentence") or "") for s in detail["audit_sentences"]),
            str(detail["audit_sentences"]),
        )
        check("operator label is the stored display name", detail["operator_labels"].get("submitted_by") == "Ni Putu Devi Parwati")

        detail_pr = p0.pr_detail("PR-1422", conn=conn)
        check("PR detail found", detail_pr is not None)
        check("Existing chip", detail_pr.get("chip") == "Existing")
        check("department from source", detail_pr.get("department") == "Kitchen")
        check("supplier from source", detail_pr.get("supplier_name") == "Harbour Fish")
        check("requester from source", detail_pr.get("requester_label") == "Devi")
        check("date from source", detail_pr.get("requested_date") == "2026-09-01")
        check("no invented amount", detail_pr.get("expected_value") is None and "amount" not in detail_pr)
        check("line qty from pr_order_lines", detail_pr["lines"] and detail_pr["lines"][0]["qty"] == 10)
        check("null price not turned into an amount", "price" not in detail_pr["lines"][0])
        check("Alchemist received is not Wolf-verified", detail_pr.get("wolf_verified") is False)
        actions = p0.pr_actions("PERS-DEVI", conn=conn)
        check("payment action stays off", actions["payment_approve"] is False)
        check("payment waiting names finance", actions["payment_waiting"] == p0.waiting_copy("finance"))

        denied = None
        try:
            p0.receive_goods(
                person_id="PERS-DEVI",
                pr_key="PR-1422",
                lines=[{"source_line_id": "1", "received_qty": 1}],
                conn=conn,
            )
        except ops.UmaOpsError as exc:
            denied = exc
        check("receive fail closed without permission", denied is not None and denied.code == "receive_permission_absent")

        grant_receive(conn)
        first = p0.receive_goods(
            person_id="PERS-DEVI",
            pr_key="PR-1422",
            lines=[{"source_line_id": "1", "received_qty": 4}],
            conn=conn,
        )
        check("partial receipt", first["status"] == "PARTIAL", str(first.get("status")))
        check("partial has evidence", bool(first.get("evidence_id")))
        snap = conn.execute(
            "SELECT status, notes, evidence_id FROM bzg_ops_receipt_events WHERE receipt_id=?",
            (first["receipt_id"],),
        ).fetchone()
        second = p0.receive_goods(
            person_id="PERS-DEVI",
            pr_key="PR-1422",
            lines=[{"source_line_id": "1", "received_qty": 6}],
            corrects_receipt_id=first["receipt_id"],
            notes="remainder",
            conn=conn,
        )
        check("complete when outstanding is zero", second["status"] == "COMPLETE", str(second))
        again = conn.execute(
            "SELECT status, notes, evidence_id FROM bzg_ops_receipt_events WHERE receipt_id=?",
            (first["receipt_id"],),
        ).fetchone()
        check("first receipt row not rewritten", tuple(again) == tuple(snap), f"{snap} -> {again}")
        blocked = False
        try:
            conn.execute(
                "UPDATE bzg_ops_receipt_events SET notes='rewritten' WHERE receipt_id=?",
                (first["receipt_id"],),
            )
        except sqlite3.Error:
            blocked = True
            conn.rollback()
        check("receipt update trigger blocks rewrite", blocked)

        check("Alchemist file hash unchanged", sha(alc_path) == before_hash)
        alc = sqlite3.connect(f"file:{alc_path}?mode=ro", uri=True)
        src_recv = alc.execute("SELECT received_qty FROM pr_order_lines WHERE id=1").fetchone()[0]
        alc.close()
        check("Alchemist received_qty unchanged", src_recv == 0, str(src_recv))
        check("Alchemist file hash unchanged", sha(alc_path) == before_hash)

        today = ops.today_cards(conn=conn, person_id="PERS-DEVI")
        kinds = {c["kind"]: c for c in today["cards"]}
        unpaid = kinds.get("legacy_unpaid_ledger")
        check("unpaid card present", unpaid is not None)
        if unpaid:
            check("unpaid is not actionable", unpaid.get("actionable") is False)
            check("unpaid waiting on finance", unpaid.get("waiting_copy") == p0.waiting_copy("finance"), str(unpaid.get("waiting_copy")))
            check("unpaid has no Open href", unpaid.get("href") is None)
        opening = kinds.get("opening_balance_required") or kinds.get("petty_cash")
        check("opening or petty card present", opening is not None)
        if opening:
            check(
                "non-actionable opening waits on policy",
                opening.get("actionable") is False and opening.get("waiting_role") == "policy",
                str({k: opening.get(k) for k in ("kind", "actionable", "waiting_role", "waiting_copy")}),
            )
        if today.get("now") and today["now"].get("actionable") is False:
            check("now waiting copy has no fake open", not today["now"].get("href"))
        else:
            check("now is an actionable card or absent", True)

        resolved_after = conn.execute(
            "SELECT COUNT(*) FROM wolf_completion_items WHERE state='RESOLVED'"
        ).fetchone()[0]
        check("completion register not resolved by this slice", resolved_after == resolved_copy)
        conn.close()
    finally:
        shutil.rmtree(td, ignore_errors=True)

    print(f"PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
