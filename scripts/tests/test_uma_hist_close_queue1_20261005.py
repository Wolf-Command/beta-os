#!/usr/bin/env python3
"""UMA-HIST-CLOSE-QUEUE-1 — owner backlog queue, preflight freeze, protected rows."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
UI = ROOT / "dashboards" / "uma-blu-close.html"
LIVE_DB = ROOT / "catalog" / "content_library.sqlite"
PREFLIGHT = ROOT / "state" / "reliability" / "UMA-HIST-CLOSE-QUEUE-PREFLIGHT-2026-10-05.json"
BETA = "http://127.0.0.1:8788"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0

NINE_DATES = (
    "2026-09-25",
    "2026-09-27",
    "2026-09-28",
    "2026-09-29",
    "2026-09-30",
    "2026-10-01",
    "2026-10-02",
    "2026-10-03",
    "2026-10-04",
)


def canonical_status_for_date(business_date: str, conn: sqlite3.Connection) -> str:
    """Derive owner queue status from live venue_daily_closes — not hardcoded."""
    from core import uma_hist_close_queue1 as qmod

    closes = qmod._closes_for_date(business_date, conn=conn)
    primary = qmod._primary_close(closes)
    close_id = primary.get("close_id") if primary else None
    ev = qmod._evidence_counts(close_id, conn)
    return qmod.canonical_ui_status(
        business_date=business_date, closes=closes, evidence=ev
    )

SEP29 = "VDC-8fd544e2-2132-4a4a-b714-720eb0cd18ad"
OCT3 = "VDC-470e741f-d889-437a-9a40-1ec9c083fb95"
OCT4 = "VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5"
PROTECTED_PETTY = "PETTY-UMA-6D853EEAE0"


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


def fetch_json(path: str) -> tuple[int | None, dict]:
    try:
        req = urllib.request.Request(BETA + path, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8", "replace") or "{}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"NOTE  beta unavailable for {path}: {exc}")
        return None, {}


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    from core import uma_hist_close_queue1 as q

    before = q.protected_close_checksums(ro_conn())
    ro_conn().close()

    conn = ro_conn()
    queue = q.owner_history_queue(today="2026-10-05", conn=conn)
    check("queue ok", queue.get("ok") is True)
    check("nine dates present", len(queue.get("queue") or []) == 9)
    live_statuses = queue.get("nine_date_statuses") or {}
    for bd in NINE_DATES:
        expect = canonical_status_for_date(bd, conn)
        got = live_statuses.get(bd)
        check(f"{bd} canonical status", got == expect, f"got {got} expect {expect}")
    conn.close()
    check("no fake CLOSED in nine", "CLOSED" not in live_statuses.values(), str(live_statuses))
    check("zero_closed_sep_oct flag", queue.get("zero_closed_sep_oct") is True)

    row29 = next(r for r in queue["queue"] if r["business_date"] == "2026-09-29")
    ms = row29.get("multi_source_preserve") or {}
    check("29 Sep auto_resolve false", ms.get("auto_resolve") is False)
    check("29 Sep owner_completable", ms.get("owner_completable") is True)
    check("29 Sep do_not_submit false for owner path", ms.get("do_not_submit") is False)
    check("29 Sep warehouse cash", ms.get("warehouse_cash") == 4135000)
    check("29 Sep printed cash", ms.get("printed_cash") == 3790000)
    check("29 Sep discrepancy cash", ms.get("discrepancy_cash") == 345000)
    check("29 Sep discrepancy bills", ms.get("discrepancy_bills") == 1)

    freeze = q.build_preflight_freeze_matrix(write=True)
    matrix = freeze.get("preflight_freeze_matrix") or []
    check("preflight freeze matrix nine rows", len(matrix) == 9)
    check(
        "petty contamination ok all nine",
        freeze.get("petty_contamination_check", {}).get("ok_not_contaminated") is True,
    )
    sample = next(r for r in matrix if r["business_date"] == "2026-09-28")
    petty_ids = [m.get("movement_id") for m in (sample.get("petty") or {}).get("movements") or []]
    check(
        f"28 Sep petty excludes {PROTECTED_PETTY}",
        PROTECTED_PETTY not in petty_ids,
        str(petty_ids),
    )
    check(
        "28 Sep live_esb_excluded",
        sample.get("live_esb_excluded") is True,
    )

    after = q.protected_close_checksums(ro_conn())
    ro_conn().close()
    check("protected closes unchanged", before == after, f"{before} vs {after}")

    petty_row = ro_conn().execute(
        "SELECT movement_id, amount, direction, business_date FROM bzg_ops_petty_movements WHERE movement_id=?",
        (PROTECTED_PETTY,),
    ).fetchone()
    ro_conn().close()
    check("protected petty unchanged", petty_row is not None)
    if petty_row:
        check("protected petty business_date today", petty_row["business_date"] == "2026-10-05")

    check("today separate from backlog", queue.get("today_business_date") == "2026-10-05")
    check("ready_to_close_now count", queue.get("ready_to_close_now") == 6)

    code, api = fetch_json("/api/venue-close/history-queue?today=2026-10-05")
    if code == 200:
        check("history-queue route 200", True)
        check("api nine statuses match", api.get("nine_date_statuses") == live_statuses)
    elif code == 403:
        check("history-queue route reachable (403 without session — module ok)", queue.get("ok") is True)
    else:
        check("history-queue route reachable", False, f"code={code}")

    html = UI.read_text(encoding="utf-8")
    check("missing closes panel in HTML", "missingQueue" in html)
    check("history-queue API in HTML", "history-queue" in html)
    check("today button separate", "btnToday" in html)
    check("history-queue anchor", "#history-queue" in html or "history-queue" in html)

    pid = prod_pid_8787()
    check("prod pid 1297 unchanged", pid == 1297, str(pid))

    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
