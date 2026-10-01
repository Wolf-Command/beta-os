#!/usr/bin/env python3
"""Wave 2.05 — performance history does not feed the current brief."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core import content_learn_wave2_05 as learn  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def main() -> int:
    catalog_mtime = learn.CATALOG_DB.stat().st_mtime_ns
    cycle_mtime = learn.CYCLE_FILE.stat().st_mtime_ns
    data = learn.load_learn()
    check(
        "staff not ready",
        data.get("staff_ready") is False
        and data.get("human_proven") is False
        and data.get("writes") is False
        and data.get("metricool_write") is False
        and data.get("metricool_read_enabled") is True
        and data.get("state") == "PARTIAL",
    )
    perf = data["performance"]
    check(
        "performance is history",
        perf.get("count") == 1103
        and perf.get("brands") == {
            "tropik": 276,
            "selo": 240,
            "umablu": 210,
            "atrium": 198,
            "habitat": 179,
        }
        and perf.get("systems") == [
            {"external_system": "metricool", "data_lane": "operational", "count": 1103}
        ]
        and perf.get("engagement_null") == 1012
        and perf.get("published_min") == "2026-07-15T23:02:34Z"
        and perf.get("published_max") == "2026-09-14T09:02:15Z"
        and perf.get("fetched_max") == "2026-09-15T07:45:19+08:00"
        and perf.get("values_omitted") is True,
        str({k: perf.get(k) for k in ("count", "brands", "engagement_null", "published_max")}),
    )
    snaps = data["snapshots"]
    check(
        "snapshots are the previous fortnight",
        snaps.get("count") == 6
        and snaps.get("brands") == ["habitat"]
        and snaps.get("performance_ids_per_snapshot") == [6, 6, 6, 6, 6, 6]
        and snaps.get("current_cycle_plans") == 0
        and snaps.get("plan_periods") == [
            {"period_start": "2026-09-14", "period_end": "2026-09-27", "count": 6}
        ],
        str(snaps),
    )
    brief = data["current_brief"]
    check(
        "current brief has no performance id",
        brief.get("brand_id") == "habitat"
        and brief.get("cycle_start") == "2026-09-28"
        and brief.get("cycle_end") == "2026-10-11"
        and brief.get("posts") == 6
        and brief.get("stories") == 28
        and brief.get("has_performance_record_id") is False
        and brief.get("prose_metricool_snapshot") == "2026-08-21T10:26:50+08:00",
        str(brief),
    )
    queue = data["publish_queue"]
    check(
        "queue is not learn-back",
        queue.get("count") == 1
        and queue.get("state") == "QUEUED"
        and queue.get("reason") == "metricool_write_blocked"
        and queue.get("publish") == "OFF",
        str(queue),
    )
    loop = data["learn"]
    check(
        "learn unavailable",
        loop.get("state") == "UNAVAILABLE"
        and loop.get("fed_into_current_brief") is False
        and loop.get("rows_written") is False,
        str(loop),
    )
    page = (ROOT / "dashboards" / "content-learn-back.html").read_text(encoding="utf-8")
    check("page title", "<title>Content learn-back</title>" in page)
    check("tiles start closed", page.count("<details>") >= 4 and "<details open" not in page)
    check("page writes no loop", "No learn-back row was written" in page)
    refused = learn.refuse_write()
    check(
        "refuse write",
        refused.get("error") == "writes_off" and refused.get("metricool_write") is False,
    )
    check(
        "files unread",
        learn.CATALOG_DB.stat().st_mtime_ns == catalog_mtime
        and learn.CYCLE_FILE.stat().st_mtime_ns == cycle_mtime,
    )
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
