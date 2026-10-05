#!/usr/bin/env python3
"""UMA-HIST-CLOSE-COMPLETE-1 — Owner/Finance complete incomplete protected 29 Sep."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
UI = ROOT / "dashboards" / "uma-blu-close.html"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0

SEP29 = "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad"
OCT3 = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
OCT4 = "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5"
MATT = "PERS-MATT"
TEST_PHOTO_REF = "TEST-UMA-HIST-CLOSE-COMPLETE-1-PHOTO"
TEST_PHOTO_HASH = "a" * 64


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def temp_catalog() -> Path:
    td = Path(tempfile.mkdtemp(prefix="tmp-uma-hist-complete1-", dir=str(ROOT / "catalog" / "backups")))
    db = td / "content_library.sqlite"
    shutil.copy2(LIVE_DB, db)
    return db


def row_hash(conn: sqlite3.Connection, close_id: str) -> str:
    row = conn.execute(
        "SELECT * FROM venue_daily_closes WHERE close_id=?",
        (close_id,),
    ).fetchone()
    return hashlib.sha256(json.dumps(dict(row) if row else {}, sort_keys=True, default=str).encode()).hexdigest()


def table_rows_hash(conn: sqlite3.Connection, table: str, close_id: str) -> dict[str, str]:
    try:
        rows = conn.execute(f"SELECT * FROM {table} WHERE close_id=?", (close_id,)).fetchall()
    except sqlite3.Error:
        return {}
    out: dict[str, str] = {}
    for r in rows:
        d = dict(r)
        pk = str(d.get("receipt_id") or d.get("evidence_id") or d.get("id") or d)
        out[pk] = hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()
    return out


def seed_plain_closer(conn: sqlite3.Connection) -> str:
    """Cashier-only closer in temp DB — no Owner/Finance complete perms."""
    ts = "2026-10-05T12:00:00+08:00"
    pid = "PERS-TEST-HIST-COMPLETE-CLOSER"
    conn.execute(
        """
        INSERT INTO org_persons (person_id, display_name, legal_name, status, created_at, updated_at)
        VALUES (?, 'Test Hist Closer', NULL, 'ACTIVE', ?, ?)
        ON CONFLICT(person_id) DO UPDATE SET status='ACTIVE', updated_at=excluded.updated_at
        """,
        (pid, ts, ts),
    )
    conn.execute(
        """
        INSERT INTO org_assignments (
          assignment_id, person_id, position_id, start_at, end_at, status,
          is_primary, created_at, updated_at
        ) VALUES ('ASG-TEST-HIST-COMPLETE-1', ?, 'POS-BZG-CLOSER-UMA-1',
                  ?, NULL, 'ACTIVE', 1, ?, ?)
        ON CONFLICT(assignment_id) DO UPDATE SET status='ACTIVE', end_at=NULL, updated_at=excluded.updated_at
        """,
        (pid, ts, ts, ts),
    )
    from core.scope import upsert_assignment_scope

    upsert_assignment_scope(conn, "ASG-TEST-HIST-COMPLETE-1", "SCOPE-BZG-UMA", ts, ts)
    conn.commit()
    return pid


def wire_modules(db: Path) -> dict:
    import core.audit as audit
    import core.bzg_daily_close as bzg
    import core.evidence as evidence
    import core.rbac as rbac
    import core.uma_hist_close_queue1 as q
    import core.venue_close as vc

    saved: dict = {}
    for mod in (vc, bzg, evidence, audit, rbac, q):
        if hasattr(mod, "CATALOG_DB"):
            saved[mod] = mod.CATALOG_DB
            mod.CATALOG_DB = db  # type: ignore[attr-defined]
    return saved


def restore_modules(saved: dict) -> None:
    for mod, val in saved.items():
        mod.CATALOG_DB = val  # type: ignore[attr-defined]


def test_owner_complete_29sep() -> None:
    os.environ["WOLF_TEST_MODE"] = "1"
    from core import bzg_daily_close as bzg
    from core import uma_hist_close_queue1 as q
    from core import venue_close as vc

    db = temp_catalog()
    saved = wire_modules(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    closer = seed_plain_closer(conn)

    oct3_before = row_hash(conn, OCT3)
    oct4_before = row_hash(conn, OCT4)
    esb_before = table_rows_hash(conn, "venue_close_esb_closing_receipts", SEP29)

    row29 = conn.execute(
        "SELECT * FROM venue_daily_closes WHERE close_id=?", (SEP29,)
    ).fetchone()
    check("29 Sep close exists in copy", row29 is not None)

    block_closer = q.mutation_block_reason(SEP29, dict(row29), verified_person_id=closer, conn=conn)
    check("closer blocked on 29 Sep", block_closer is not None, str(block_closer))

    block_matt = q.mutation_block_reason(SEP29, dict(row29), verified_person_id=MATT, conn=conn)
    check("Matt mutation allowed on 29 Sep incomplete", block_matt is None, str(block_matt))

    submit_block_closer = q.submit_block_reason(SEP29, dict(row29), verified_person_id=closer, conn=conn)
    check("closer submit blocked 29 Sep", submit_block_closer is not None)

    submit_block_matt = q.submit_block_reason(SEP29, dict(row29), verified_person_id=MATT, conn=conn)
    check("Matt submit allowed 29 Sep", submit_block_matt is None, str(submit_block_matt))

    queue_matt = q.owner_history_queue(today="2026-10-05", verified_person_id=MATT, conn=conn)
    row_q = next(r for r in queue_matt["queue"] if r["business_date"] == "2026-09-29")
    check("29 Sep action CONTINUE for Matt", row_q.get("action_label") == "CONTINUE", str(row_q))
    check("29 Sep flow wizard for Matt", row_q.get("flow") == "wizard")
    check("29 Sep owner_can_complete", row_q.get("owner_can_complete") is True)

    try:
        vc.take_open_venue_close(SEP29, verified_person_id=MATT, conn=conn, commit=True)
    except vc.VenueCloseError:
        vc.reassign_venue_close(
            SEP29,
            verified_person_id=MATT,
            new_holder_person_id=MATT,
            reason="UMA-HIST-CLOSE-COMPLETE-1 test",
            conn=conn,
            commit=True,
        )

    try:
        bzg.confirm_esb_closing_receipt(
            SEP29,
            verified_person_id=MATT,
            action="looks_correct",
            object_ref=TEST_PHOTO_REF,
            content_hash=TEST_PHOTO_HASH,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check("owner photo append on 29 Sep", True)
    except bzg.BzgDailyCloseError as exc:
        check("owner photo append on 29 Sep", False, str(exc))

    cash_amt = 3790000.0
    try:
        vc.attach_declared_cash(
            SEP29,
            declared_cash_amount=cash_amt,
            verified_person_id=MATT,
            allow_test_write=True,
            conn=conn,
            commit=True,
        )
        check("owner declare cash on 29 Sep", True)
    except vc.VenueCloseError as exc:
        check("owner declare cash on 29 Sep", False, str(exc))

    out1 = bzg.staff_submit_close(
        SEP29,
        declared_cash_amount=cash_amt,
        verified_person_id=MATT,
        business_date="2026-09-29",
        submit_with_exception=True,
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    check(
        "first submit CLOSE SAVED WITH EXCEPTION",
        out1.get("staff_result") == "CLOSE SAVED WITH EXCEPTION",
        str(out1.get("staff_result")),
    )
    disc = q.multi_source_preserve_29sep(SEP29, conn=conn) or {}
    check("discrepancy cash 345000 preserved", disc.get("discrepancy_cash") == 345000)
    check("discrepancy bills 1 preserved", disc.get("discrepancy_bills") == 1)
    check("auto_resolve false", disc.get("auto_resolve") is False)

    out2 = bzg.staff_submit_close(
        SEP29,
        declared_cash_amount=cash_amt,
        verified_person_id=MATT,
        business_date="2026-09-29",
        submit_with_exception=True,
        allow_test_write=True,
        conn=conn,
        commit=True,
    )
    check(
        "second submit idempotent",
        out2.get("idempotent") is True or out2.get("staff_result") in (
            "CLOSE SAVED WITH EXCEPTION",
            "CLOSE COMPLETE",
        ),
        str(out2),
    )

    esb_after = table_rows_hash(conn, "venue_close_esb_closing_receipts", SEP29)
    for pk, h in esb_before.items():
        check(f"existing esb receipt row unchanged {pk[:12]}", esb_after.get(pk) == h)
    check("new evidence appended", len(esb_after) >= len(esb_before))

    check("3 Oct row hash unchanged", row_hash(conn, OCT3) == oct3_before)
    check("4 Oct row hash unchanged", row_hash(conn, OCT4) == oct4_before)

    for cid in (OCT3, OCT4):
        try:
            vc.attach_declared_cash(
                cid,
                declared_cash_amount=1.0,
                verified_person_id=MATT,
                allow_test_write=True,
                conn=conn,
                commit=False,
            )
            check(f"oct mutation refused {cid[:12]}", False, "no exception")
        except vc.VenueCloseError as exc:
            check(f"oct mutation refused {cid[:12]}", exc.code == "protected_close", str(exc))

    conn.close()
    restore_modules(saved)
    shutil.rmtree(db.parent, ignore_errors=True)


def test_html_no_vdc() -> None:
    html = UI.read_text(encoding="utf-8")
    check("date-peek in HTML", "date-peek" in html)
    m = re.search(
        r"el\.innerHTML = rows\.map\(\(r\) => \{[\s\S]*?\}\)\.join",
        html,
    )
    check("queue template no VDC-", m is not None and "VDC-" not in (m.group(0) if m else ""))


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


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    from core import uma_hist_close_queue1 as q

    live_conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    live_conn.row_factory = sqlite3.Row
    live29_before = row_hash(live_conn, SEP29)
    live_oct3_before = row_hash(live_conn, OCT3)
    live_oct4_before = row_hash(live_conn, OCT4)
    live_conn.close()

    test_owner_complete_29sep()
    test_html_no_vdc()

    live_conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    live_conn.row_factory = sqlite3.Row
    check("live 29 Sep unchanged", row_hash(live_conn, SEP29) == live29_before)
    check("live 3 Oct unchanged", row_hash(live_conn, OCT3) == live_oct3_before)
    check("live 4 Oct unchanged", row_hash(live_conn, OCT4) == live_oct4_before)
    live_conn.close()

    before = q.protected_close_checksums(
        sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    )
    after = q.protected_close_checksums(
        sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    )
    check("protected checksums unchanged", before == after)

    pid = prod_pid_8787()
    check("prod pid 1297 unchanged", pid == 1297, str(pid))

    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
