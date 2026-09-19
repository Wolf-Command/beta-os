#!/usr/bin/env python3
"""Uma legacy projection — temp sqlite + optional live Alchemist (read-only).

Slice BF-uma-legacy-projection-20260919. No canonical copy. No invented float.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

os.environ.pop("WOLF_ALCHEMIST_DB", None)
os.environ["WOLF_TEST_MODE"] = "1"

from core import uma_alchemist_ro as alc  # noqa: E402
from core import uma_ops_console as ops  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _schema(conn: sqlite3.Connection) -> None:
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
        CREATE TABLE petty_cash (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          entry_date TEXT,
          flow TEXT,
          category TEXT,
          description TEXT,
          amount REAL,
          logged_by_name TEXT,
          created_at TEXT
        );
        CREATE TABLE ledger (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          amount REAL,
          payment_status TEXT,
          hold INTEGER DEFAULT 0
        );
        """
    )
    conn.execute(
        """
        INSERT INTO pr_orders
          (pr_num, requested_by, vendor, order_date, status, notes, created_at, invoice_total)
        VALUES ('PR-1422', 'Devi', 'Harbour Fish', '2026-09-01', 'Awaiting Devi',
                'Prawns', '2026-09-01T08:00:00+08:00', 150000)
        """
    )
    conn.execute(
        """
        INSERT INTO pr_orders
          (pr_num, requested_by, vendor, order_date, status, notes, created_at, invoice_total)
        VALUES ('PR-1400', 'Devi', 'Garden Supply', '2026-09-02', 'Received',
                'Herbs', '2026-09-02T08:00:00+08:00', 80000)
        """
    )
    conn.execute(
        """
        INSERT INTO pr_orders
          (pr_num, requested_by, vendor, order_date, status, notes, created_at, invoice_total)
        VALUES ('PR-1390', 'Devi', 'Dairy Co', '2026-09-03', 'Paid',
                'Milk', '2026-09-03T08:00:00+08:00', 40000)
        """
    )
    conn.execute(
        """
        INSERT INTO petty_cash
          (entry_date, flow, category, description, amount, logged_by_name, created_at)
        VALUES ('2026-09-18', 'Cash Out (Spend)', 'Staff Meal', 'lunch', 300000,
                'Uma Blu', '2026-09-18T14:19:04+08:00')
        """
    )
    conn.execute(
        """
        INSERT INTO ledger (amount, payment_status, hold)
        VALUES (120000, 'unpaid', 0)
        """
    )
    conn.commit()


def _stamp_ok(row: dict) -> bool:
    prov = row.get("provenance") or {}
    return (
        row.get("legacy") is True
        and row.get("record_origin") == "alchemist"
        and prov.get("source") == "alchemist"
        and prov.get("table")
        and prov.get("source_id") is not None
    )


def main() -> int:
    src = (SCRIPTS / "core" / "uma_alchemist_ro.py").read_text(encoding="utf-8")
    check("adapter opens mode=ro", "mode=ro" in src and "query_only" in src)
    check("adapter does not insert", "insert into" not in src.lower())
    check("adapter does not update rows", "update " not in src.lower())
    check("cutover helper returns None on the prepared file", alc.cutover_at() is None)
    cutover = json.loads((ROOT / "state" / "uma" / "cutover.json").read_text(encoding="utf-8"))
    check(
        "cutover.json keeps cutover_at null",
        cutover.get("cutover_at") is None and cutover.get("sources") == ["alchemist"],
        str(cutover),
    )

    bills = (ROOT / "dashboards" / "bzg-uma-blu-bills.html").read_text(encoding="utf-8")
    petty_html = (ROOT / "dashboards" / "bzg-uma-blu-petty.html").read_text(encoding="utf-8")
    today_html = (ROOT / "dashboards" / "bzg-uma-blu.html").read_text(encoding="utf-8")
    for name, text in (
        ("bills", bills),
        ("petty", petty_html),
        ("today", today_html),
    ):
        check(f"{name} shows Existing chip", "Existing" in text)
        check(f"{name} does not render source_id", "source_id" not in text)
    check("bills shows pr_num", "pr_num" in bills)
    check("history shows pr_num not a raw int", "pr_num" in today_html and "No history yet." in today_html)
    check(
        "petty keeps opening-balance banner over movements",
        "Opening cash balance needed" in petty_html
        and "do not set an opening balance" in petty_html
        and "No petty movements yet." in petty_html,
    )
    serve = (SCRIPTS / "serve_beta.py").read_text(encoding="utf-8")
    check("bills payload carries fixture_notice", "fixture_notice_for" in serve)

    td = tempfile.mkdtemp(prefix="uma-legacy-", dir=str(ROOT / "state"))
    try:
        missing = Path(td) / "missing.db"
        os.environ["WOLF_ALCHEMIST_DB"] = str(missing)
        check("missing db returns no prs", alc.project_prs(limit=10) == [])
        check("missing db is INACCESSIBLE", alc.source_status() == "INACCESSIBLE")
        summary_miss = alc.project_attention_summary()
        check(
            "missing summary does not invent a float",
            summary_miss.get("source_status") == "INACCESSIBLE"
            and summary_miss.get("unpaid_ledger_sum") is None
            and "opening_float" not in summary_miss,
            str(summary_miss),
        )

        db = Path(td) / "alchemist.sqlite"
        conn = sqlite3.connect(db)
        _schema(conn)
        conn.close()
        os.environ["WOLF_ALCHEMIST_DB"] = str(db)

        try:
            ro = alc.connect_readonly(db)
            try:
                ro.execute("CREATE TABLE should_fail (id INTEGER)")
                refused = False
            except sqlite3.OperationalError:
                refused = True
            finally:
                ro.close()
        except sqlite3.Error:
            refused = False
        check("readonly connection refuses writes", refused)

        prs = alc.project_prs(limit=20)
        by_num = {p.get("pr_num"): p for p in prs}
        check("fixture prs project", set(by_num) >= {"PR-1422", "PR-1400", "PR-1390"}, str(set(by_num)))
        check("every pr has legacy provenance", all(_stamp_ok(p) for p in prs))
        wait = by_num["PR-1422"]
        check(
            "Awaiting Devi maps to waiting approval",
            wait.get("state") == "REQUESTED"
            and wait.get("display_status") == "Waiting approval"
            and wait.get("needs_attention") is True,
            str(wait.get("state")),
        )
        paid = by_num["PR-1390"]
        check(
            "Paid is recorded in Alchemist, not Wolf verified",
            paid.get("display_status") == "Recorded as paid in Alchemist"
            and paid.get("state") not in ("PAID_CLAIMED", "PAYMENT_VERIFIED")
            and paid.get("payment_evidence_id") is None,
            str(paid.get("state")),
        )
        check("attention_only skips Paid", all(p.get("pr_num") != "PR-1390" for p in alc.project_prs(limit=20, attention_only=True)))

        moves = alc.project_petty_movements(limit=10)
        check("petty movement projects", len(moves) == 1 and _stamp_ok(moves[0]))
        check(
            "petty maps flow and never sets opening_float",
            moves[0].get("direction") == "OUT"
            and moves[0].get("flow") == "Cash Out (Spend)"
            and moves[0].get("amount") == 300000
            and "opening_float" not in moves[0],
            str(moves[0].get("direction")),
        )
        hist = alc.project_history_events(limit=10)
        sentences = [h.get("sentence") or "" for h in hist]
        check(
            "history sentences are human",
            any(s == "2026-09-01 · Purchase request recorded · Alchemist" for s in sentences)
            and any(s == "2026-09-18 · Petty movement recorded · Alchemist" for s in sentences)
            and all(_stamp_ok(h) for h in hist),
            str(sentences),
        )
        summary = alc.project_attention_summary()
        check(
            "attention summary counts",
            summary.get("source_status") == "OK"
            and summary.get("awaiting_devi_count") == 1
            and summary.get("received_count") == 1
            and summary.get("unpaid_ledger_count") == 1
            and summary.get("unpaid_ledger_sum") == 120000
            and summary.get("recent_petty")
            and "opening_float" not in summary,
            str({k: summary.get(k) for k in ("awaiting_devi_count", "received_count", "unpaid_ledger_count")}),
        )

        cat = Path(td) / "content_library.sqlite"
        live_cat = ROOT / "catalog" / "content_library.sqlite"
        if live_cat.is_file():
            shutil.copy2(live_cat, cat)
        else:
            sqlite3.connect(cat).close()
        ops.CATALOG_DB = cat
        from core import audit as audit
        from core import venue_close as venue_close

        audit.CATALOG_DB = cat
        venue_close.CATALOG_DB = cat
        wolf = ops.db_connect(cat)
        ops.ensure_schema(wolf)
        wolf.execute("DELETE FROM bzg_ops_purchase_requests")
        wolf.execute("DELETE FROM bzg_ops_petty_movements")
        wolf.execute("DELETE FROM bzg_ops_petty_days")
        ops.insert_pr_row(
            pr_id="PR-WOLF-LIVE",
            state="REQUESTED",
            supplier_name="Wolf supplier",
            purpose="Live wolf request",
            example=False,
            conn=wolf,
        )
        ops.insert_pr_row(
            pr_id="PR-1422",
            state="REQUESTED",
            supplier_name="Should lose to wolf",
            purpose="Duplicate num",
            example=False,
            conn=wolf,
        )
        ops.insert_pr_row(
            pr_id="PR-UMA-EXAMPLE-WAIT",
            state="REQUESTED",
            supplier_name="Example produce supplier",
            purpose="Weekend greens",
            example=True,
            conn=wolf,
        )
        wolf.commit()
        before_pr = wolf.execute("SELECT COUNT(*) FROM bzg_ops_purchase_requests").fetchone()[0]
        before_petty = wolf.execute("SELECT COUNT(*) FROM bzg_ops_petty_movements").fetchone()[0]

        listed = ops.list_prs(conn=wolf, limit=50)
        after_pr = wolf.execute("SELECT COUNT(*) FROM bzg_ops_purchase_requests").fetchone()[0]
        check("list_prs does not copy legacy into bzg_ops", before_pr == after_pr, f"{before_pr} -> {after_pr}")
        check(
            "wolf non-example leads the bills payload",
            listed and listed[0].get("pr_id") == "PR-WOLF-LIVE" and not listed[0].get("legacy"),
            str(listed[0].get("pr_id") if listed else None),
        )
        legacy_nums = [p.get("pr_num") for p in listed if p.get("legacy")]
        check("legacy prs follow wolf", "PR-1400" in legacy_nums and "PR-1390" in legacy_nums, str(legacy_nums))
        check(
            "duplicate pr_num keeps the wolf row",
            sum(1 for p in listed if p.get("pr_id") == "PR-1422" or p.get("pr_num") == "PR-1422") == 1
            and any(p.get("pr_id") == "PR-1422" and not p.get("legacy") for p in listed),
        )
        check(
            "examples do not dominate when legacy is live",
            all(not p.get("example") for p in listed),
        )
        check(
            "bills rows carry provenance",
            any(_stamp_ok(p) for p in listed),
        )

        petty = ops.list_petty(conn=wolf)
        after_petty = wolf.execute("SELECT COUNT(*) FROM bzg_ops_petty_movements").fetchone()[0]
        check("list_petty does not copy movements", before_petty == after_petty)
        check(
            "petty payload is legacy movements and float NOT_FOUND",
            petty.get("float_status") == "NOT_FOUND"
            and petty.get("opening_float") is None
            and petty.get("movements")
            and all(m.get("legacy") for m in petty["movements"])
            and all("opening_float" not in m for m in petty["movements"])
            and petty.get("fixture_notice") is False,
            str(petty.get("float_status")),
        )

        history = ops.list_history(conn=wolf, limit=20)
        events = history.get("events") or []
        check(
            "history payload has legacy chronology",
            any(
                e.get("legacy") and "Purchase request recorded · Alchemist" in (e.get("sentence") or "")
                for e in events
            )
            and any(_stamp_ok(e) for e in events if e.get("legacy")),
            str([e.get("sentence") for e in events][:4]),
        )

        today = ops.today_cards(conn=wolf)
        kinds = [c.get("kind") for c in today.get("cards") or []]
        check("today payload ok", today.get("ok") is True and "prs_waiting_approval" in kinds, str(kinds))
        check(
            "today float stays NOT_FOUND",
            today.get("float_status") == "NOT_FOUND" and today.get("opening_float") is None,
            str(today.get("float_status")),
        )
        check("today hides fixture notice when legacy is live", today.get("fixture_notice") is False)
        waiting = next(c for c in today["cards"] if c.get("kind") == "prs_waiting_approval")
        received = next(c for c in today["cards"] if c.get("kind") == "received_follow_up")
        check(
            "today waiting card is wolf-first",
            any(i.get("pr_id") == "PR-WOLF-LIVE" for i in waiting.get("items") or []),
        )
        check(
            "today received card carries legacy provenance",
            any((i.get("provenance") or {}).get("source") == "alchemist" for i in received.get("items") or [])
            and any(i.get("pr_num") == "PR-1400" for i in received.get("items") or []),
        )
        check(
            "today keeps opening-balance blocker",
            any(c.get("kind") == "petty_cash" and "OPENING BALANCE" in (c.get("title") or "") for c in today["cards"])
            and any("do not set an opening balance" in (c.get("why") or "") for c in today["cards"]),
        )
        check(
            "today unpaid ledger is not a verified payment",
            any(c.get("kind") == "legacy_unpaid_ledger" for c in today["cards"]),
        )
        proj = today.get("legacy_projection") or {}
        check(
            "today legacy projection has provenance",
            (proj.get("provenance") or {}).get("source") == "alchemist"
            or any(_stamp_ok(p) for p in proj.get("recent_petty") or []),
        )
        issues = ops.list_issues(conn=wolf)
        check(
            "paid legacy rows are not missing-payment issues",
            not any(
                "PR-1390" in (i.get("label") or "") or i.get("pr_id") == "PR-1390"
                for i in issues.get("issues") or []
            ),
        )
        wolf.close()
    finally:
        os.environ.pop("WOLF_ALCHEMIST_DB", None)
        shutil.rmtree(td, ignore_errors=True)

    live = alc.DEFAULT_DB
    if not live.is_file():
        print("SKIP  live alchemist db not readable")
    else:
        os.environ["WOLF_ALCHEMIST_DB"] = str(live)
        try:
            live_rows = alc.project_prs(limit=5)
            check(
                "live alchemist projects at least one pr",
                len(live_rows) > 0 and all(_stamp_ok(p) for p in live_rows),
                str(len(live_rows)),
            )
            check("live read leaves cutover_at unset", alc.cutover_at() is None)
        except Exception as exc:  # noqa: BLE001
            check("live alchemist projects at least one pr", False, str(exc))
        finally:
            os.environ.pop("WOLF_ALCHEMIST_DB", None)

    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
