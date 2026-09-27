#!/usr/bin/env python3
"""CAP-GGV-01 content-path read. Counts the existing catalog. Writes nothing."""
from __future__ import annotations

import inspect
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["WOLF_TEST_MODE"] = "1"
os.environ.pop("WOLF_ALLOW_LIVE_AUDIT", None)
os.environ.pop("WOLF_CANONICAL_WRITE_OVERRIDE", None)

from core import ggv_strategy_machine as base  # noqa: E402

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
EVIDENCE_ID = "EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153"
FORBIDDEN_KEYS = {
    "text",
    "theme",
    "objectives",
    "script_body",
    "title",
    "strategy_json",
    "cadence",
    "voice_rules",
    "content_mix_guide",
    "feed_target",
    "story_target",
    "digests",
    "body",
    "body_json",
    "display_name",
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def _ledger_counts() -> tuple[int, int, int, str | None]:
    conn = _ro(CATALOG)
    try:
        evidence = int(conn.execute("SELECT COUNT(*) FROM core_evidence_records").fetchone()[0])
        exceptions = int(conn.execute("SELECT COUNT(*) FROM core_governance_exceptions").fetchone()[0])
        approvals = int(conn.execute("SELECT COUNT(*) FROM core_approval_decisions").fetchone()[0])
        status = conn.execute(
            "SELECT status FROM core_evidence_records WHERE evidence_id=?",
            (EVIDENCE_ID,),
        ).fetchone()
    finally:
        conn.close()
    return evidence, exceptions, approvals, None if status is None else str(status[0])


def _oracle() -> dict:
    conn = _ro(CATALOG)
    try:
        plans = conn.execute(
            "SELECT data_lane, COUNT(*) FROM content_plans GROUP BY data_lane"
        ).fetchall()
        with_strategy = {"operational": 0, "test": 0}
        learn_items = 0
        learn_unknown = False
        sources: set[str] = set()
        connected = 0
        for lane, raw in conn.execute(
            "SELECT data_lane, strategy_json FROM content_plans"
        ):
            if not raw or not str(raw).strip():
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                if lane == "operational":
                    learn_unknown = True
                continue
            if not isinstance(obj, dict) or not obj:
                continue
            if lane in with_strategy:
                with_strategy[lane] += 1
            if lane != "operational":
                continue
            items = obj.get("important_learnings")
            if items is None:
                continue
            if not isinstance(items, list):
                learn_unknown = True
                continue
            for item in items:
                if not isinstance(item, dict):
                    learn_unknown = True
                    break
                learn_items += 1
                source = item.get("source")
                if isinstance(source, str) and source.strip():
                    sources.add(source.strip())
            label = (obj.get("disconnected") or {}).get("performance_data") if isinstance(obj.get("disconnected"), dict) else None
            if label == "connected":
                connected += 1
        assets = int(conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0])
        revisions = conn.execute(
            "SELECT data_lane, COUNT(*) FROM plan_revisions GROUP BY data_lane"
        ).fetchall()
        cards = conn.execute(
            "SELECT data_lane, COUNT(*) FROM content_cards GROUP BY data_lane"
        ).fetchall()
        planner = int(conn.execute("SELECT COUNT(*) FROM content_planner").fetchone()[0])
        linked = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM content_planner
                WHERE raw_asset_id IS NOT NULL
                  AND EXISTS (SELECT 1 FROM assets AS a WHERE a.id = content_planner.raw_asset_id)
                """
            ).fetchone()[0]
        )
        learn_tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND lower(name) LIKE '%learn%'"
        ).fetchall()
    finally:
        conn.close()
    return {
        "plans": {row[0]: int(row[1]) for row in plans},
        "with_strategy": with_strategy,
        "learn_items": "UNKNOWN" if learn_unknown else learn_items,
        "sources": sorted(sources),
        "connected": connected,
        "assets": assets,
        "revisions": {row[0]: int(row[1]) for row in revisions},
        "cards": {row[0]: int(row[1]) for row in cards},
        "planner": planner,
        "linked": linked,
        "learn_tables": [row[0] for row in learn_tables],
    }


def _kind(report: dict, name: str) -> dict:
    for row in report.get("kinds") or []:
        if row.get("kind") == name:
            return row
    return {}


def _forbidden(obj: object, trail: str = "") -> str:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_KEYS:
                return trail + "." + str(key)
            found = _forbidden(value, trail + "." + str(key))
            if found:
                return found
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            found = _forbidden(value, f"{trail}[{index}]")
            if found:
                return found
    return ""


def main() -> int:
    before_counts = _ledger_counts()
    ledger_before = LEDGER.read_bytes()
    oracle = _oracle()
    report = base.read_content_path()
    again = base.read_content_path()
    check("two reads match", report == again)
    check("read ok", report.get("ok") is True and report.get("cap") == "CAP-GGV-01")
    check("cap stays the content machine", report.get("read") == "content_path")
    check(
        "not a live machine",
        report.get("live_strategy_machine") is False
        and report.get("skeleton_filled") is False
        and report.get("proved") is False
        and report.get("current") is False
        and report.get("governed_learning") is False,
    )
    check(
        "no invented figures",
        report.get("strategy_score") is None
        and report.get("revenue") is None
        and report.get("learn_outcome") is None
        and report.get("payment") is None
        and report.get("payment_executed") is False,
    )
    check(
        "no external write",
        report.get("metricool_called") is False
        and report.get("metricool_write") is False
        and report.get("catalog_write") is False
        and report.get("ledger_write") is False
        and report.get("bank_write") is False
        and report.get("books_write") is False
        and report.get("cr_resolved") is False,
    )
    check(
        "publish stays on the other row",
        report.get("publish_cap") == "CAP-GGV-02"
        and report.get("publish_tested_here") is False
        and report.get("approved_is_published") is False,
    )
    check(
        "people gates stay unset",
        report.get("staff_ready") is False
        and report.get("human_commissioned") is False
        and report.get("operating_adoption") == "NOT MEASURED",
    )
    flags = report.get("honesty") or {}
    check(
        "ledger stays built",
        flags.get("ledger_maturity") == "BUILT"
        and flags.get("maturity_ceiling") == "BUILT"
        and report.get("ledger_maturity") == "BUILT",
    )
    check("cr stays open", flags.get("cr_state") == "OPEN" and flags.get("cr_resolved") is False)
    check("statement text stays out", _forbidden(report) == "", _forbidden(report))

    strategy = _kind(report, "strategy")
    plan = _kind(report, "plan")
    asset = _kind(report, "asset")
    workflow = _kind(report, "workflow")
    learn = _kind(report, "learn")
    check(
        "five kinds",
        [row.get("kind") for row in report.get("kinds") or []]
        == ["strategy", "plan", "asset", "workflow", "learn"],
    )
    check(
        "strategy matches stored operational plans",
        strategy.get("stored_count") == oracle["with_strategy"]["operational"]
        and strategy.get("test_lane_excluded") == oracle["with_strategy"]["test"]
        and strategy.get("stored_count", 0) > 0
        and strategy.get("test_lane_excluded", 0) > 0
        and strategy.get("strategy_score") is None,
        str(strategy.get("stored_count")),
    )
    check(
        "plan matches stored operational plans",
        plan.get("stored_count") == oracle["plans"].get("operational")
        and plan.get("test_lane_excluded") == oracle["plans"].get("test")
        and plan.get("operational_cards") == oracle["cards"].get("operational")
        and plan.get("test_cards_excluded") == oracle["cards"].get("test")
        and plan.get("stored_count", 0) > 0,
        str(plan.get("stored_count")),
    )
    check(
        "asset matches the library and names the missing lane",
        asset.get("lane") == "UNKNOWN"
        and asset.get("stored_count") == oracle["assets"]
        and asset.get("stored_count", 0) > 0
        and asset.get("planner_raw_asset_exists") == oracle["linked"],
        str(asset.get("stored_count")),
    )
    check(
        "workflow matches operational revisions",
        workflow.get("stored_count") == oracle["revisions"].get("operational")
        and workflow.get("test_lane_excluded") == oracle["revisions"].get("test")
        and workflow.get("stored_count", 0) > 0
        and workflow.get("planner_lane") == "UNKNOWN"
        and workflow.get("planner_stored_count") == oracle["planner"]
        and workflow.get("approved_is_published") is False,
        str(workflow.get("stored_count")),
    )
    check(
        "learn matches stored items and stays ungoverned",
        learn.get("stored_count") == oracle["learn_items"]
        and learn.get("sources") == oracle["sources"]
        and learn.get("learning_library") == "NOT CONNECTED"
        and learn.get("learning_tables") == []
        and learn.get("governed_learning") is False
        and learn.get("learn_outcome") is None
        and isinstance(learn.get("stored_count"), int)
        and learn.get("stored_count", 0) > 0
        and learn.get("stored_performance_label_connected_plans") == oracle["connected"]
        and oracle["connected"] > 0,
        str(learn.get("stored_count")),
    )
    distinct = learn.get("distinct_statements")
    check(
        "distinct learn statements are a count",
        isinstance(distinct, int) and 0 < distinct <= learn.get("stored_count"),
        str(distinct),
    )
    check("learning library table absent", oracle["learn_tables"] == [])

    skeleton = base.build_framework()
    check(
        "skeleton stays empty",
        skeleton.get("empty") is True
        and skeleton.get("recorded_count") == 0
        and skeleton.get("live_strategy_machine") is False
        and skeleton.get("governed_learning") is False,
    )
    refused = False
    try:
        base.refuse_fill({})
    except base.StrategyMachineError as exc:
        refused = exc.code == "slots_refused"
    check("fill still refused", refused)

    opener = inspect.getsource(base._open_catalog_ro)
    check("catalog open is read-only", "mode=ro" in opener)
    reader = inspect.getsource(base.read_content_path)
    check("reader has no store statement", "INSERT INTO" not in reader and "UPDATE " not in reader)

    refused_prod = False
    try:
        base.read_content_path("/tmp/wolf-system/not-a-catalog.sqlite")
    except base.StrategyMachineError as exc:
        refused_prod = exc.code == "not_beta"
    check("prod path refused", refused_prod)

    after_counts = _ledger_counts()
    check("evidence count unchanged", after_counts[0] == before_counts[0] == 4, str(after_counts[0]))
    check("exception count unchanged", after_counts[1] == before_counts[1] == 3, str(after_counts[1]))
    check("approval count unchanged", after_counts[2] == before_counts[2] == 9, str(after_counts[2]))
    check(
        "preserved evidence stays invalidated",
        before_counts[3] == "INVALIDATED" and after_counts[3] == "INVALIDATED",
        str(after_counts[3]),
    )
    check("ledger file unchanged", LEDGER.read_bytes() == ledger_before)
    check("oracle still matches after the read", _oracle() == oracle)

    print(f"PASS={PASS} FAIL={FAIL}")
    print("EXIT: SUCCESS" if FAIL == 0 else "EXIT: FAILED")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
