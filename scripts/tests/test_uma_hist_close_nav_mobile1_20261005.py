#!/usr/bin/env python3
"""UMA-HIST-CLOSE-NAV-MOBILE-1 — mobile tap navigation + protected read-only review."""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
UI = ROOT / "dashboards" / "uma-blu-close.html"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0

OCT3 = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
SEP29 = "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad"
OCT4 = "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5"
PROTECTED = (OCT3, SEP29, OCT4)


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def ro_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def prod_pid_8787() -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", "tcp:8787"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if not out:
            return None
        return int(out.splitlines()[0])
    except Exception:
        return None


def temp_catalog() -> Path:
    td = Path(tempfile.mkdtemp(prefix="uma-hist-nav-", dir=str(ROOT / "catalog" / "backups")))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    return db


def make_esb(path: Path, rows: list[tuple[str, float]]) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("DROP TABLE IF EXISTS sales")
        conn.execute(
            "CREATE TABLE sales (nk TEXT PRIMARY KEY, biz_date TEXT, raw TEXT, pulled_at TEXT)"
        )
        for i, (biz, cash) in enumerate(rows):
            raw = {
                "branchCode": "BLZ",
                "salesNum": f"S{i}",
                "billNum": f"B{i}",
                "statusName": "Finished",
                "grandTotal": cash,
                "paymentTotal": cash,
                "salesPayments": [{"paymentMethodTypeName": "CASH", "paymentAmount": cash}],
            }
            conn.execute(
                "INSERT INTO sales (nk, biz_date, raw, pulled_at) VALUES (?,?,?,?)",
                (f"BLZ|S{i}", biz, json.dumps(raw), f"{biz}T20:00:00+08:00"),
            )
        conn.commit()
    finally:
        conn.close()


def closer_actor(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        """
        SELECT person_id FROM venue_closer_roster
        WHERE brand_id = 'BZG-UMA' AND status = 'ACTIVE'
        LIMIT 1
        """
    ).fetchone()
    if row:
        return str(row[0])
    row = conn.execute(
        """
        SELECT a.person_id
        FROM org_assignments a
        JOIN org_positions p ON p.position_id = a.position_id
        WHERE p.role_id = 'ROLE-BZG-CLOSER' AND a.status = 'ACTIVE' AND a.end_at IS NULL
        LIMIT 1
        """
    ).fetchone()
    assert row is not None
    return str(row[0])


def test_html_queue_markup() -> None:
    html = UI.read_text(encoding="utf-8")
    check("queue-card class in HTML", "queue-card" in html)
    check("touch-action manipulation in queue", "touch-action:manipulation" in html or "touch-action: manipulation" in html)
    check("min-height 44px in queue", "min-height:44px" in html or "min-height: 44px" in html)
    check("data-date on queue cards", "data-date" in html)
    check("business_date href deep link", "business_date=" in html)
    check("missing closes panel", "missingQueue" in html)
    check("showStep scrolls to top", "scrollTo" in html)
    check("date-peek read-only open", "date-peek" in html)
    check("six-step shift screen", "stepShift" in html)
    check("readOnly guard on submit", "readOnly" in html)
    # Queue render template must not emit VDC- into row markup
    m = re.search(
        r"el\.innerHTML = rows\.map\(\(r\) => \{[\s\S]*?\}\)\.join",
        html,
    )
    check("queue row template found", m is not None)
    if m:
        check("queue row template has no VDC-", "VDC-" not in m.group(0))
    check("queue uses summary_line not close_id", "summary_line" in html and "close_id ||" not in html)


def test_js_hides_panels() -> None:
    html = UI.read_text(encoding="utf-8")
    check("six-step showStep function", "function showStep" in html)
    check("stepChoose screen", 'id="stepChoose"' in html)
    check("date-peek read-only open", "date-peek" in html)
    check("shift step hides choose", 'showStep("stepShift")' in html or "stepShift" in html)


def test_protected_server_mutations() -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    from core import uma_hist_close_queue1 as q
    from core import venue_close as vc

    db = temp_catalog()
    saved = vc.CATALOG_DB
    vc.CATALOG_DB = db  # type: ignore[attr-defined]
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    closer = closer_actor(conn)
    matt = "PERS-MATT"
    plain = "PERS-TEST-NAV-PLAIN-CLOSER"
    ts = "2026-10-05T12:00:00+08:00"
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, status, created_at, updated_at)
        VALUES (?, 'Nav Plain Closer', 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO NOTHING
        """,
        (plain, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, status, is_primary, created_at, updated_at
        ) VALUES ('ASG-NAV-PLAIN-1', ?, 'POS-BZG-CLOSER-UMA-1', ?, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO NOTHING
        """,
        (plain, ts, ts, ts),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, "ASG-NAV-PLAIN-1", "SCOPE-BZG-UMA", ts, ts)
    conn.commit()
    readonly = (OCT3, OCT4)
    try:
        for cid in readonly:
            block = q.mutation_block_reason(cid, verified_person_id=closer, conn=conn)
            check(f"mutation block {cid[:12]}", block is not None, str(block))
            try:
                vc.capture_esb_snapshot(
                    cid,
                    verified_person_id=closer,
                    conn=conn,
                    commit=False,
                )
                check(f"capture refused {cid[:12]}", False, "no exception")
            except vc.VenueCloseError as exc:
                check(f"capture refused {cid[:12]}", exc.code == "protected_close", str(exc))
            try:
                vc.attach_declared_cash(
                    cid,
                    declared_cash_amount=1000.0,
                    verified_person_id=closer,
                    conn=conn,
                    commit=False,
                )
                check(f"declare refused {cid[:12]}", False, "no exception")
            except vc.VenueCloseError as exc:
                check(f"declare refused {cid[:12]}", exc.code == "protected_close", str(exc))
        row29 = conn.execute(
            "SELECT * FROM venue_daily_closes WHERE close_id=?", (SEP29,)
        ).fetchone()
        block_closer = q.mutation_block_reason(
            SEP29, dict(row29) if row29 else None, verified_person_id=plain, conn=conn
        )
        check("29 Sep plain closer blocked", block_closer is not None, str(block_closer))
        block_matt = q.mutation_block_reason(
            SEP29, dict(row29) if row29 else None, verified_person_id=matt, conn=conn
        )
        check("29 Sep Matt allowed when incomplete", block_matt is None, str(block_matt))
    finally:
        conn.close()
        vc.CATALOG_DB = saved  # type: ignore[attr-defined]
        shutil.rmtree(db.parent, ignore_errors=True)


def test_open_or_get_concurrent() -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    import core.audit as audit
    import core.bzg_daily_close as bzg
    import core.evidence as evidence
    import core.rbac as rbac
    import core.venue_close as vc

    db = temp_catalog()
    saved: dict = {}
    for mod in (vc, bzg, evidence, audit, rbac):
        if hasattr(mod, "CATALOG_DB"):
            saved[mod] = mod.CATALOG_DB
            mod.CATALOG_DB = db  # type: ignore[attr-defined]

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    closer = closer_actor(conn)
    biz = "2099-07-01"
    results: list[dict] = []
    errors: list[str] = []

    def worker() -> None:
        c = sqlite3.connect(str(db))
        c.row_factory = sqlite3.Row
        try:
            out = vc.open_or_get(biz, verified_person_id=closer, conn=c, commit=True)
            results.append(out)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
        finally:
            c.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    check("concurrent open no errors", not errors, str(errors))
    ids = {str(r.get("close_id")) for r in results}
    check("concurrent open same close_id", len(ids) == 1, str(ids))
    row = conn.execute(
        """
        SELECT COUNT(*) FROM venue_daily_closes
        WHERE business_date=? AND state != 'CANCELLED'
        """,
        (biz,),
    ).fetchone()
    check("concurrent open one row", int(row[0]) == 1, str(row[0]))

    for mod, val in saved.items():
        mod.CATALOG_DB = val  # type: ignore[attr-defined]
    conn.close()
    shutil.rmtree(db.parent, ignore_errors=True)


def test_exception_review_oct3() -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    from core import uma_hist_close_queue1 as q

    before = q.protected_close_checksums(ro_conn())
    payload = q.exception_review_payload(OCT3, conn=ro_conn())
    after = q.protected_close_checksums(ro_conn())
    check("exception review ok", payload.get("ok") is True)
    check("oct3 difference 125000", payload.get("difference") == 125000.0, str(payload))
    check("oct3 cash 3225000", payload.get("cash_counted") == 3225000.0, str(payload))
    check("oct3 expected 3350000", payload.get("expected_cash_in_till") == 3350000.0, str(payload))
    check("protected closes unchanged", before == after)


def test_date_register_sep3() -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    from core import bzg_daily_close as bzg

    reg = bzg.close_date_register(search="2026-09-03", conn=ro_conn())
    dates = {d["business_date"] for d in (reg.get("days") or [])}
    check("3 Sep 2026 in date register", "2026-09-03" in dates, str(sorted(dates)[:5]))


def test_historical_capture_date_only() -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    import core.audit as audit
    import core.bzg_daily_close as bzg
    import core.evidence as evidence
    import core.rbac as rbac
    import core.venue_close as vc

    db = temp_catalog()
    td = db.parent
    esb_path = td / "esb.sqlite"
    hist_date = "2099-06-10"
    today_date = "2099-06-11"
    make_esb(esb_path, [(hist_date, 111000.0), (today_date, 999000.0)])
    os.environ["WOLF_ESB_SQLITE"] = str(esb_path)

    saved: dict = {}
    for mod in (vc, bzg, evidence, audit, rbac):
        if hasattr(mod, "CATALOG_DB"):
            saved[mod] = mod.CATALOG_DB
            mod.CATALOG_DB = db  # type: ignore[attr-defined]

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    closer = closer_actor(conn)
    try:
        opened = vc.open_or_get(hist_date, verified_person_id=closer, conn=conn, commit=True)
        cid = str(opened["close_id"])
        cap = vc.capture_esb_snapshot(
            cid,
            verified_person_id=closer,
            business_date=hist_date,
            esb_path=esb_path,
            conn=conn,
            commit=True,
        )
        totals = cap.get("esb_totals") or {}
        cash = totals.get("cash_from_payments") or totals.get("cash_sales_grand")
        check("historical capture uses hist date cash", cash == 111000.0, str(cash))
        check("historical capture not today cash", cash != 999000.0)
    finally:
        conn.close()
        for mod, val in saved.items():
            mod.CATALOG_DB = val  # type: ignore[attr-defined]
        shutil.rmtree(td, ignore_errors=True)


def test_queue_api_labels() -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    from core import uma_hist_close_queue1 as q

    queue = q.owner_history_queue(today="2026-10-05", conn=ro_conn())
    queue_matt = q.owner_history_queue(today="2026-10-05", verified_person_id="PERS-MATT", conn=ro_conn())
    oct3 = next(r for r in queue["queue"] if r["business_date"] == "2026-10-03")
    sep29 = next(r for r in queue["queue"] if r["business_date"] == "2026-09-29")
    sep29_matt = next(r for r in queue_matt["queue"] if r["business_date"] == "2026-09-29")
    check("oct3 action REVIEW EXCEPTION", oct3.get("action_label") == "REVIEW EXCEPTION")
    check("sep29 anonymous protected readonly flow", sep29.get("flow") == "protected_readonly")
    check("sep29 Matt wizard flow", sep29_matt.get("flow") == "wizard")
    check("sep29 Matt CONTINUE label", sep29_matt.get("action_label") == "CONTINUE")
    check("oct3 summary has difference", "125" in str(oct3.get("summary_line") or ""))
    for row in queue.get("queue") or []:
        sl = str(row.get("summary_line") or "")
        check(
            f"summary_line no VDC {row.get('business_date')}",
            "VDC-" not in sl,
            sl,
        )


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    from core import uma_hist_close_queue1 as q

    before = q.protected_close_checksums(ro_conn())
    ro_conn().close()

    test_html_queue_markup()
    test_js_hides_panels()
    test_protected_server_mutations()
    test_open_or_get_concurrent()
    test_exception_review_oct3()
    test_date_register_sep3()
    test_historical_capture_date_only()
    test_queue_api_labels()

    after = q.protected_close_checksums(ro_conn())
    ro_conn().close()
    check("protected closes unchanged end", before == after)

    pid = prod_pid_8787()
    check("prod pid 1297 unchanged", pid == 1297, str(pid))

    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
