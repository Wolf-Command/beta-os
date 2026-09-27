#!/usr/bin/env python3
"""CAP-GGV-01 strategy / plan / asset / workflow / learn skeleton v1 (Beta only).

Decision served: 2026-09-20 plan
docs/deliveries/GROK-PLAN-GGV-STRATEGY-MACHINE-V1-2026-09-20.md.
Owner order KEEP BUILDING WITHOUT MATT. Lane ggv-strategy-machine-v1 on
mission owner-autonomous-20260920-w8 after intg-connector-cap-tests-v1 DONE
(b6b7b2e / 6c60a3a). CR-8c1fa12404180c02 stays OPEN.
intel-learning-policy-v1 stays parked. Bound beta-ggv-ops-safe.

Names the strategy, plan, asset, workflow, and learn slots and leaves every
slot empty. An empty framework is not a live strategy machine and not proof
of governed learning. This module does not invent a strategy score, revenue,
or a learn outcome. It does not write Production, Alchemist, Metricool,
Zayen books, a bank, a payment, Cloudflare, Access, the Model C ledger, or
the completion row. CAP-GGV-01 stays BUILT. The ceiling label is BUILT.
PROVEN and READY are not invented.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

BETA_ROOT = Path("/Users/wolfterminal/beta-os").resolve()
DEFAULT_DB = BETA_ROOT / "catalog" / "ggv_strategy_machine.sqlite"
LIVE_DEFAULT_DB = DEFAULT_DB.resolve()
CATALOG_DB = BETA_ROOT / "catalog" / "content_library.sqlite"
LEDGER_JSON = BETA_ROOT / "state" / "model-c-baseline-assessments.json"

OWNER_PERSON = "PERS-MATT"
CR_ID = "CR-8c1fa12404180c02"
CAP_ID = "CAP-GGV-01"
SCHEMA_ID = "wolf.cap-ggv-01.strategy-machine.v1"
BOUND = "beta-ggv-ops-safe"

KIND_IDS = ("strategy", "plan", "asset", "workflow", "learn")
MATURITY = frozenset({"ABSENT", "SPECIFIED", "BUILT", "PROVEN", "READY"})

EVIDENCE_KINDS: tuple[dict[str, Any], ...] = (
    {
        "kind": "strategy",
        "label": "Strategy",
        "slot": "empty",
        "evidence": None,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "current": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "metricool_write": False,
        "payment": None,
        "payment_executed": False,
        "why": "Named strategy slot. Empty is not a live strategy machine and not proof of governed learning.",
    },
    {
        "kind": "plan",
        "label": "Plan",
        "slot": "empty",
        "evidence": None,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "current": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "metricool_write": False,
        "payment": None,
        "payment_executed": False,
        "why": "Named plan slot. Empty is not a live strategy machine and not a current plan.",
    },
    {
        "kind": "asset",
        "label": "Asset",
        "slot": "empty",
        "evidence": None,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "current": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "metricool_write": False,
        "payment": None,
        "payment_executed": False,
        "why": "Named asset slot. Empty is not a content asset and not a Metricool write.",
    },
    {
        "kind": "workflow",
        "label": "Workflow",
        "slot": "empty",
        "evidence": None,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "current": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "metricool_write": False,
        "payment": None,
        "payment_executed": False,
        "why": "Named workflow slot. Empty is not a live workflow and not a money move.",
    },
    {
        "kind": "learn",
        "label": "Learn",
        "slot": "empty",
        "evidence": None,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "current": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "metricool_write": False,
        "payment": None,
        "payment_executed": False,
        "why": "Named learn slot. Empty is not proof of governed learning and not a learn outcome.",
    },
)

GAPS: tuple[str, ...] = (
    "The framework is empty.",
    "An empty framework is not a live strategy machine.",
    "An empty framework is not proof of governed learning.",
    "An empty framework is not READY.",
    "PROVEN is not invented.",
    "READY is not invented.",
    "Strategy scores, revenue, and learn outcomes are not invented.",
    "No Metricool write.",
    "No payment is executed.",
    "No bank write.",
    "No Zayen or books write.",
    "No Alchemist write.",
    "Cloudflare is not mutated.",
    "Access is not mutated.",
    "The completion row is not resolved.",
    "CAP-GGV-01 stays BUILT.",
    "The ceiling label is BUILT.",
)

HONESTY = {
    "cap": CAP_ID,
    "bound": BOUND,
    "slice": "ggv_strategy_machine_v1",
    "slice_label": "BUILT",
    "read_only": True,
    "on_disk": False,
    "empty_honest": True,
    "empty_is_machine": False,
    "empty_is_learning": False,
    "empty_is_ready": False,
    "proved": False,
    "live_strategy_machine": False,
    "governed_learning": False,
    "current": False,
    "strategy_score": None,
    "revenue": None,
    "learn_outcome": None,
    "metricool_write": False,
    "metricool_called": False,
    "payment": None,
    "money": None,
    "payment_executed": False,
    "bank_write": False,
    "books_write": False,
    "zayen_write": False,
    "alchemist_write": False,
    "cloudflare_mutated": False,
    "access_mutated": False,
    "score_changed": False,
    "production": False,
    "wolf_system_write": False,
    "anon_fail_closed": True,
    "owner_read": True,
    "cr_mutated": False,
    "model_c_write": False,
    "model_c_maturity_raised": False,
    "invented_proven": False,
    "invented_ready": False,
    "ledger_write": False,
}


class StrategyMachineError(ValueError):
    """Fail closed. Does not invent a strategy machine, a learn outcome, or PROVEN."""

    def __init__(self, message: str, *, code: str = "invalid"):
        super().__init__(message)
        self.code = code


def _under_test_process() -> bool:
    if (os.environ.get("WOLF_TEST_MODE") or "").strip() == "1":
        return True
    argv0 = " ".join(sys.argv[:2]) if sys.argv else ""
    return "scripts/tests" in argv0.replace("\\", "/")


def _assert_beta_path(resolved: Path) -> None:
    low = str(resolved).lower()
    name = resolved.name.lower()
    if "alchemist" in low:
        raise StrategyMachineError(
            "strategy framework refuses an Alchemist path",
            code="alchemist_refused",
        )
    if "wolf-system" in low:
        raise StrategyMachineError(
            "strategy framework refuses a wolf-system path",
            code="not_beta",
        )
    if "zayen" in low or "books.sqlite" in name or name == "books" or "/books/" in low:
        raise StrategyMachineError(
            "Zayen finance books are not written from this framework.",
            code="books_refused",
        )
    if "metricool" in name or "metricool" in low:
        raise StrategyMachineError(
            "A Metricool write is refused. This framework does not post content.",
            code="metricool_refused",
        )
    if "bank" in name:
        raise StrategyMachineError(
            "A bank write is refused. No money moves.",
            code="bank_refused",
        )
    if "payment" in name:
        raise StrategyMachineError(
            "A payment is not executed on this framework. No amount is kept.",
            code="payment_refused",
        )
    if "/production" in low or name == "money.sqlite":
        raise StrategyMachineError(
            "strategy framework refuses a production path",
            code="not_beta",
        )
    try:
        resolved.resolve().relative_to(BETA_ROOT)
        return
    except ValueError:
        pass
    import tempfile

    tmp = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.resolve().relative_to(tmp)
    except ValueError as exc:
        raise StrategyMachineError(
            "strategy framework refuses a path outside Beta or a test fixture",
            code="not_beta",
        ) from exc


def _row_state(data: Any) -> str:
    row = data.get(CAP_ID) if isinstance(data, dict) else None
    if not isinstance(row, list) or not row:
        return "UNKNOWN"
    state = str(row[0]).strip().upper()
    if state not in MATURITY:
        return "UNKNOWN"
    return state


def ledger_cap_state(ledger_path: Path | str | None = None) -> str:
    """Read CAP-GGV-01. Does not write the ledger."""
    path = Path(ledger_path) if ledger_path else LEDGER_JSON
    _assert_beta_path(path.resolve())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "UNKNOWN"
    return _row_state(data)


def ceiling_for(_state: str) -> str:
    """BUILT label only. At most BUILT. Does not write the ledger."""
    return "BUILT"


def load_cr_binding(catalog_db: Path | str | None = None) -> dict[str, Any]:
    """Read CR-8c1fa12404180c02. Does not upsert, resolve, or harvest."""
    out: dict[str, Any] = {
        "cr_id": CR_ID,
        "cr_bound": True,
        "cr_present": False,
        "cr_state": None,
        "cr_blocker": None,
        "cr_capability": CAP_ID,
        "cr_title": None,
        "cr_next_action": None,
        "cr_resolved": False,
    }
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    if not path.is_file():
        return out
    _assert_beta_path(path.resolve())
    uri = path.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return out
    try:
        row = conn.execute(
            """
            SELECT state, blocker_class, capability, title, next_action
            FROM wolf_completion_items WHERE id=?
            """,
            (CR_ID,),
        ).fetchone()
    except sqlite3.Error:
        return out
    finally:
        conn.close()
    if row is None:
        return out
    out["cr_present"] = True
    out["cr_state"] = row[0]
    out["cr_blocker"] = row[1]
    out["cr_capability"] = row[2] or CAP_ID
    out["cr_title"] = row[3]
    out["cr_next_action"] = row[4]
    out["cr_resolved"] = row[0] == "RESOLVED"
    return out


def honesty_flags(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    state = ledger_cap_state(ledger_path)
    flags = dict(HONESTY)
    flags.update(load_cr_binding(catalog_db))
    flags["ledger_maturity"] = state
    flags["maturity"] = state
    flags["maturity_ceiling"] = ceiling_for(state)
    flags["proven"] = state == "PROVEN"
    flags["ready"] = state == "READY"
    flags["built"] = state == "BUILT"
    flags["invented_proven"] = False
    flags["invented_ready"] = False
    flags["model_c_write"] = False
    flags["model_c_maturity_raised"] = False
    flags["cr_mutated"] = False
    flags["empty_is_machine"] = False
    flags["empty_is_learning"] = False
    flags["empty_is_ready"] = False
    flags["proved"] = False
    flags["live_strategy_machine"] = False
    flags["governed_learning"] = False
    flags["current"] = False
    flags["strategy_score"] = None
    flags["revenue"] = None
    flags["learn_outcome"] = None
    flags["metricool_write"] = False
    flags["metricool_called"] = False
    flags["payment"] = None
    flags["money"] = None
    flags["payment_executed"] = False
    flags["bank_write"] = False
    flags["books_write"] = False
    flags["zayen_write"] = False
    flags["alchemist_write"] = False
    flags["cloudflare_mutated"] = False
    flags["access_mutated"] = False
    flags["score_changed"] = False
    flags["on_disk"] = False
    flags["bound"] = BOUND
    flags["ledger_write"] = False
    return flags


def schema_document() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "additionalProperties": False,
        "required": ["kind", "subject", "status", "evidence_note"],
        "properties": {
            "kind": {"type": "string", "enum": list(KIND_IDS)},
            "subject": {"type": "string"},
            "status": {"type": "string", "enum": ["NOTED"]},
            "evidence_note": {
                "type": "string",
                "description": "Not accepted. A note would not be a live strategy machine.",
            },
        },
        "kind_enum": list(KIND_IDS),
        "status_enum": ["NOTED"],
        "writes_accepted": False,
        "payment_property": False,
        "bank_property": False,
        "books_property": False,
        "metricool_property": False,
        "strategy_score_property": False,
        "revenue_property": False,
        "learn_outcome_property": False,
        "current_property": False,
        "cloudflare_property": False,
        "access_property": False,
        "proven_property": False,
        "ready_property": False,
    }


def kind_slots() -> list[dict[str, Any]]:
    """Named slots. Each one is empty. Empty is not a live strategy machine."""
    return [dict(row) for row in EVIDENCE_KINDS]


def _quiet_read() -> dict[str, Any]:
    return {
        "empty": True,
        "empty_is_machine": False,
        "empty_is_learning": False,
        "empty_is_ready": False,
        "proved": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "current": False,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "metricool_write": False,
        "metricool_called": False,
        "payment": None,
        "payment_executed": False,
        "bank_write": False,
        "books_write": False,
        "zayen_write": False,
        "alchemist_write": False,
        "ledger_write": False,
        "cr_resolved": False,
    }


def read_kind(kind_id: str) -> dict[str, Any]:
    token = (kind_id or "").strip().lower()
    for row in EVIDENCE_KINDS:
        if row["kind"] == token:
            return {
                "ok": True,
                "kind": dict(row),
                **_quiet_read(),
                "honesty": honesty_flags(),
            }
    raise StrategyMachineError("Unknown strategy slot.", code="not_found")


def build_framework(
    ledger_path: Path | str | None = None,
    catalog_db: Path | str | None = None,
) -> dict[str, Any]:
    """Owner read of the skeleton. Does not create a framework file."""
    flags = honesty_flags(ledger_path, catalog_db)
    return {
        "ok": True,
        "cap": CAP_ID,
        "bound": BOUND,
        "schema_id": SCHEMA_ID,
        "schema": schema_document(),
        "recorded_count": 0,
        "money": None,
        "cloudflare_mutated": False,
        "access_mutated": False,
        "score_changed": False,
        "on_disk": False,
        "kinds": kind_slots(),
        "rows": [],
        "gaps": list(GAPS),
        "framework_skeleton": "BUILT",
        **_quiet_read(),
        "cr_resolved": flags["cr_resolved"] if flags["cr_state"] == "RESOLVED" else False,
        "honesty": flags,
    }


def _open_catalog_ro(catalog_db: Path | str | None) -> sqlite3.Connection:
    path = Path(catalog_db) if catalog_db else CATALOG_DB
    resolved = path.resolve()
    _assert_beta_path(resolved)
    if not resolved.is_file():
        raise StrategyMachineError(
            "content catalog is not on disk",
            code="catalog_absent",
        )
    uri = resolved.as_uri() + "?mode=ro"
    try:
        return sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise StrategyMachineError(
            "content catalog could not be opened read-only",
            code="catalog_unreadable",
        ) from exc


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _learn_from_strategy_json(raw: str | None) -> dict[str, Any]:
    """Count stored learning items. Does not keep the statement text."""
    empty = {
        "parse": "blank",
        "nonempty": False,
        "items": 0,
        "sources": [],
        "surfaces": [],
        "digests": [],
        "performance_label": None,
    }
    if raw is None or not str(raw).strip():
        return empty
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "parse": "UNKNOWN",
            "nonempty": False,
            "items": "UNKNOWN",
            "sources": [],
            "surfaces": [],
            "digests": [],
            "performance_label": "UNKNOWN",
        }
    if not isinstance(obj, dict):
        return {
            "parse": "UNKNOWN",
            "nonempty": False,
            "items": "UNKNOWN",
            "sources": [],
            "surfaces": [],
            "digests": [],
            "performance_label": "UNKNOWN",
        }
    items = obj.get("important_learnings")
    sources: list[str] = []
    surfaces: list[str] = []
    digests: list[str] = []
    if items is None:
        count: int | str = 0
    elif not isinstance(items, list):
        count = "UNKNOWN"
    else:
        count = 0
        for item in items:
            if not isinstance(item, dict):
                count = "UNKNOWN"
                break
            count += 1
            source = item.get("source")
            surface = item.get("surface")
            if isinstance(source, str) and source.strip():
                sources.append(source.strip())
            if isinstance(surface, str) and surface.strip():
                surfaces.append(surface.strip())
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                digests.append(hashlib.sha256(text.strip().encode("utf-8")).hexdigest())
    label = None
    disconnected = obj.get("disconnected")
    if isinstance(disconnected, dict):
        raw_label = disconnected.get("performance_data")
        if isinstance(raw_label, str):
            label = raw_label.strip() or None
    return {
        "parse": "ok" if count != "UNKNOWN" else "UNKNOWN",
        "nonempty": bool(obj),
        "items": count,
        "sources": sources,
        "surfaces": surfaces,
        "digests": digests if count != "UNKNOWN" else [],
        "performance_label": label,
    }


def read_content_path(
    catalog_db: Path | str | None = None,
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """Read the existing content catalog onto the five kinds.

    Does not fill the skeleton, write the catalog, call Metricool, or raise
    the ledger. Test-lane plans are not operational. A stored performance
    label is not a Metricool call. No learning-library table means governed
    learning stays false. Publish stays on CAP-GGV-02.
    """
    flags = honesty_flags(ledger_path, catalog_db)
    conn = _open_catalog_ro(catalog_db)
    try:
        names = _table_names(conn)
        required = (
            "content_plans",
            "content_cards",
            "assets",
            "content_planner",
            "plan_revisions",
            "brands",
        )
        missing = [name for name in required if name not in names]
        if missing:
            return {
                "ok": False,
                "cap": CAP_ID,
                "read": "content_path",
                "missing_tables": missing,
                "operational_count": "UNKNOWN",
                "strategy_score": None,
                "revenue": None,
                "learn_outcome": None,
                "live_strategy_machine": False,
                "governed_learning": False,
                "metricool_called": False,
                "metricool_write": False,
                "payment_executed": False,
                "catalog_write": False,
                "ledger_write": False,
                "skeleton_filled": False,
                "publish_cap": "CAP-GGV-02",
                "publish_tested_here": False,
                "honesty": flags,
            }
        learning_tables = sorted(
            name for name in names if "learn" in name.lower()
        )
        plan_rows = conn.execute(
            """
            SELECT data_lane, status, COUNT(*)
            FROM content_plans
            GROUP BY data_lane, status
            ORDER BY data_lane, status
            """
        ).fetchall()
        strategy_rows = conn.execute(
            """
            SELECT id, data_lane, status, review_state, strategy_json
            FROM content_plans
            ORDER BY id
            """
        ).fetchall()
        card_rows = conn.execute(
            """
            SELECT data_lane, card_type, status, COUNT(*)
            FROM content_cards
            GROUP BY data_lane, card_type, status
            ORDER BY data_lane, card_type, status
            """
        ).fetchall()
        asset_rows = conn.execute(
            """
            SELECT brand, status, COUNT(*)
            FROM assets
            GROUP BY brand, status
            ORDER BY brand, status
            """
        ).fetchall()
        planner_rows = conn.execute(
            """
            SELECT brand, status, COUNT(*),
                   SUM(CASE WHEN raw_asset_id IS NOT NULL THEN 1 ELSE 0 END),
                   SUM(CASE
                         WHEN raw_asset_id IS NOT NULL
                          AND EXISTS (
                            SELECT 1 FROM assets AS a WHERE a.id = content_planner.raw_asset_id
                          )
                         THEN 1 ELSE 0 END),
                   SUM(CASE
                         WHEN core_approval_request_id IS NOT NULL
                          AND length(trim(core_approval_request_id)) > 0
                         THEN 1 ELSE 0 END)
            FROM content_planner
            GROUP BY brand, status
            ORDER BY brand, status
            """
        ).fetchall()
        revision_rows = conn.execute(
            """
            SELECT data_lane, role, COUNT(*)
            FROM plan_revisions
            GROUP BY data_lane, role
            ORDER BY data_lane, role
            """
        ).fetchall()
        brand_rows = conn.execute(
            "SELECT id, status FROM brands ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    operational_plans = 0
    test_plans = 0
    other_plans = 0
    operational_with_strategy = 0
    test_with_strategy = 0
    learn_items = 0
    learn_unknown = False
    learn_sources: set[str] = set()
    learn_surfaces: set[str] = set()
    learn_digests: set[str] = set()
    performance_connected_plans = 0
    review_counts: dict[str, int] = {}
    operational_status: dict[str, int] = {}
    for row in strategy_rows:
        lane = row[1] or ""
        status = row[2] or ""
        review = row[3] if row[3] else "blank"
        parsed = _learn_from_strategy_json(row[4])
        if lane == "operational":
            operational_plans += 1
            operational_status[status] = operational_status.get(status, 0) + 1
            review_key = f"{status}:{review}"
            review_counts[review_key] = review_counts.get(review_key, 0) + 1
            if parsed["nonempty"] and parsed["parse"] == "ok":
                operational_with_strategy += 1
            if parsed["items"] == "UNKNOWN":
                learn_unknown = True
            elif isinstance(parsed["items"], int):
                learn_items += parsed["items"]
                learn_digests.update(parsed["digests"])
            learn_sources.update(parsed["sources"])
            learn_surfaces.update(parsed["surfaces"])
            if parsed["performance_label"] == "connected":
                performance_connected_plans += 1
        elif lane == "test":
            test_plans += 1
            if parsed["nonempty"] and parsed["parse"] == "ok":
                test_with_strategy += 1
        else:
            other_plans += 1

    def _sum_lane(rows: list[tuple], lane: str) -> int:
        return sum(int(row[-1]) for row in rows if row[0] == lane)

    operational_cards = _sum_lane(card_rows, "operational")
    test_cards = _sum_lane(card_rows, "test")
    operational_revisions = _sum_lane(revision_rows, "operational")
    test_revisions = _sum_lane(revision_rows, "test")
    asset_count = sum(int(row[2]) for row in asset_rows)
    planner_count = sum(int(row[2]) for row in planner_rows)
    planner_linked = sum(int(row[3] or 0) for row in planner_rows)
    planner_linked_existing = sum(int(row[4] or 0) for row in planner_rows)
    planner_core_approval = sum(int(row[5] or 0) for row in planner_rows)

    plan_groups = [
        {"data_lane": row[0], "status": row[1], "n": int(row[2])}
        for row in plan_rows
    ]
    card_groups = [
        {
            "data_lane": row[0],
            "card_type": row[1],
            "status": row[2],
            "n": int(row[3]),
        }
        for row in card_rows
    ]
    asset_groups = [
        {"brand": row[0], "status": row[1], "n": int(row[2])}
        for row in asset_rows
    ]
    planner_groups = [
        {
            "brand": row[0],
            "status": row[1],
            "n": int(row[2]),
            "raw_asset_id_set": int(row[3] or 0),
            "raw_asset_exists": int(row[4] or 0),
            "core_approval_request_set": int(row[5] or 0),
        }
        for row in planner_rows
    ]
    revision_groups = [
        {"data_lane": row[0], "role": row[1], "n": int(row[2])}
        for row in revision_rows
    ]

    learn_count: int | str = "UNKNOWN" if learn_unknown else learn_items
    kinds = [
        {
            "kind": "strategy",
            "source": "content_plans.strategy_json",
            "lane": "operational",
            "stored_count": operational_with_strategy,
            "test_lane_excluded": test_with_strategy,
            "strategy_score": None,
        },
        {
            "kind": "plan",
            "source": "content_plans",
            "lane": "operational",
            "stored_count": operational_plans,
            "test_lane_excluded": test_plans,
            "other_lane": other_plans,
            "status_counts": operational_status,
            "review_counts": review_counts,
            "operational_cards": operational_cards,
            "test_cards_excluded": test_cards,
        },
        {
            "kind": "asset",
            "source": "assets",
            "lane": "UNKNOWN",
            "stored_count": asset_count,
            "by_brand_status": asset_groups,
            "planner_raw_asset_id_set": planner_linked,
            "planner_raw_asset_exists": planner_linked_existing,
        },
        {
            "kind": "workflow",
            "source": "plan_revisions",
            "lane": "operational",
            "stored_count": operational_revisions,
            "test_lane_excluded": test_revisions,
            "by_role": [
                row for row in revision_groups if row["data_lane"] == "operational"
            ],
            "planner_lane": "UNKNOWN",
            "planner_source": "content_planner",
            "planner_stored_count": planner_count,
            "planner_by_brand_status": planner_groups,
            "planner_core_approval_request_set": planner_core_approval,
            "approved_is_published": False,
        },
        {
            "kind": "learn",
            "source": "content_plans.strategy_json.important_learnings",
            "lane": "operational",
            "stored_count": learn_count,
            "distinct_statements": (
                "UNKNOWN" if learn_unknown else len(learn_digests)
            ),
            "sources": sorted(learn_sources),
            "surfaces": sorted(learn_surfaces),
            "learning_library": "NOT CONNECTED" if not learning_tables else "UNKNOWN",
            "learning_tables": learning_tables,
            "governed_learning": False,
            "learn_outcome": None,
            "stored_performance_label_connected_plans": performance_connected_plans,
        },
    ]
    return {
        "ok": True,
        "cap": CAP_ID,
        "read": "content_path",
        "bound": BOUND,
        "kinds": kinds,
        "plan_groups": plan_groups,
        "card_groups": card_groups,
        "asset_groups": asset_groups,
        "planner_groups": planner_groups,
        "revision_groups": revision_groups,
        "brands": [{"id": row[0], "status": row[1]} for row in brand_rows],
        "skeleton_filled": False,
        "live_strategy_machine": False,
        "governed_learning": False,
        "proved": False,
        "current": False,
        "strategy_score": None,
        "revenue": None,
        "learn_outcome": None,
        "metricool_called": False,
        "metricool_write": False,
        "payment": None,
        "payment_executed": False,
        "bank_write": False,
        "books_write": False,
        "catalog_write": False,
        "ledger_write": False,
        "cr_resolved": False,
        "publish_cap": "CAP-GGV-02",
        "publish_tested_here": False,
        "approved_is_published": False,
        "staff_ready": False,
        "human_commissioned": False,
        "operating_adoption": "NOT MEASURED",
        "ledger_maturity": flags.get("ledger_maturity"),
        "honesty": flags,
    }


def refuse_payment(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "A payment is not executed on this framework. No amount is kept.",
        code="payment_refused",
    )


def refuse_bank(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "A bank write is refused. No money moves.",
        code="bank_refused",
    )


def refuse_books(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Zayen finance books are not written from this framework.",
        code="books_refused",
    )


def refuse_metricool(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "A Metricool write is refused. This framework does not post content.",
        code="metricool_refused",
    )


def refuse_current(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Strategy scores, revenue, and learn outcomes are not invented. Empty is not a live strategy machine.",
        code="current_refused",
    )


def refuse_cloudflare(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Cloudflare is not mutated from this framework.",
        code="cloudflare_refused",
    )


def refuse_access(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Access is not mutated from this framework.",
        code="access_refused",
    )


def refuse_proven(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "PROVEN is refused. The ceiling label is BUILT. The live ledger stays BUILT.",
        code="proven_refused",
    )


def refuse_ready(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "READY is refused. An empty framework is not READY.",
        code="ready_refused",
    )


def refuse_resolve(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Resolving the completion row is refused. CR-8c1fa12404180c02 stays open.",
        code="resolve_refused",
    )


def refuse_production(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Production mutation is refused.",
        code="production_refused",
    )


def refuse_score(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "Score gaming is refused. The ledger and credits are not written.",
        code="score_refused",
    )


def refuse_fill(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "The framework stays empty. A filled slot would not be a live strategy machine.",
        code="slots_refused",
    )


def refuse_alchemist(_body: dict | None = None) -> None:
    raise StrategyMachineError(
        "An Alchemist write is refused.",
        code="alchemist_refused",
    )


def refuse_external_write(body: dict | None = None) -> None:
    payload = body or {}
    if isinstance(payload, dict):
        for key in payload:
            token = str(key).strip().lower().replace("_", "-")
            if token in {"payment", "payments", "money", "price", "amount", "invoice", "paid"}:
                refuse_payment(payload)
            if token in {"bank", "transfer", "payout", "withdraw"}:
                refuse_bank(payload)
            if token in {"zayen", "books", "journal"}:
                refuse_books(payload)
            if token in {"metricool", "metricool-write"}:
                refuse_metricool(payload)
            if token in {
                "strategy-score",
                "revenue",
                "learn-outcome",
                "outcome",
                "current",
            }:
                refuse_current(payload)
            if token in {"cloudflare", "cf", "zone", "tunnel"}:
                refuse_cloudflare(payload)
            if token in {"access", "cf-access", "zero-trust"}:
                refuse_access(payload)
            if token in {"proven", "prove"}:
                refuse_proven(payload)
            if token == "ready":
                refuse_ready(payload)
            if token in {"resolve", "cr-resolved"}:
                refuse_resolve(payload)
            if token in {"production", "production-mutate"}:
                refuse_production(payload)
            if token in {"score", "credits", "green"}:
                refuse_score(payload)
            if token in {"alchemist"}:
                refuse_alchemist(payload)
            if token in {
                "fill",
                "note",
                "evidence",
                "evidence-note",
                "slots-filled",
                "strategy",
                "plan",
                "asset",
                "workflow",
                "learn",
            }:
                refuse_fill(payload)
    raise StrategyMachineError(
        "This framework does not store a strategy, a plan, a payment, or a learn outcome.",
        code="writes_refused",
    )


def refuse_store(db_path: Path | str) -> None:
    """Refuse a destination. Does not create the file."""
    resolved = Path(db_path).resolve()
    if resolved == CATALOG_DB.resolve() or resolved.name == "content_library.sqlite":
        raise StrategyMachineError(
            "strategy framework does not write the content catalog",
            code="catalog_refused",
        )
    if resolved.name == "model-c-baseline-assessments.json":
        raise StrategyMachineError(
            "strategy framework does not write the Model C ledger",
            code="ledger_write_refused",
        )
    _assert_beta_path(resolved)
    if resolved == LIVE_DEFAULT_DB and _under_test_process():
        if (os.environ.get("WOLF_ALLOW_LIVE_GGV_STRATEGY") or "").strip() != "1":
            raise StrategyMachineError(
                "test mode refuses the live strategy framework path",
                code="live_guard",
            )
    raise StrategyMachineError(
        "The framework stays empty. Empty is not a live strategy machine.",
        code="slots_refused",
    )


def resolve_cr(*_args: Any, **_kwargs: Any) -> None:
    refuse_resolve({})


def mark_proven(*_args: Any, **_kwargs: Any) -> None:
    refuse_proven({})


def mark_ready(*_args: Any, **_kwargs: Any) -> None:
    refuse_ready({})


def mark_current(*_args: Any, **_kwargs: Any) -> None:
    refuse_current({})


def write_metricool(*_args: Any, **_kwargs: Any) -> None:
    refuse_metricool({})


def move_money(*_args: Any, **_kwargs: Any) -> None:
    refuse_payment({})


def _present(value: str | None) -> bool:
    return (value or "").strip() != ""


def guard_query(
    *,
    payment: str | None = None,
    money: str | None = None,
    bank: str | None = None,
    zayen: str | None = None,
    books: str | None = None,
    metricool: str | None = None,
    strategy_score: str | None = None,
    revenue: str | None = None,
    learn_outcome: str | None = None,
    current: str | None = None,
    cloudflare: str | None = None,
    access: str | None = None,
    prove: str | None = None,
    proven: str | None = None,
    ready: str | None = None,
    resolve: str | None = None,
    production: str | None = None,
    fill: str | None = None,
    score: str | None = None,
    alchemist: str | None = None,
    write: str | None = None,
) -> None:
    if _present(payment) or _present(money):
        refuse_payment({})
    if _present(bank):
        refuse_bank({})
    if _present(zayen) or _present(books):
        refuse_books({})
    if _present(metricool):
        refuse_metricool({})
    if (
        _present(strategy_score)
        or _present(revenue)
        or _present(learn_outcome)
        or _present(current)
    ):
        refuse_current({})
    if _present(cloudflare):
        refuse_cloudflare({})
    if _present(access):
        refuse_access({})
    if _present(proven) or _present(prove):
        refuse_proven({})
    if _present(ready):
        refuse_ready({})
    if _present(resolve):
        refuse_resolve({})
    if _present(production):
        refuse_production({})
    if _present(score):
        refuse_score({})
    if _present(alchemist):
        refuse_alchemist({})
    if _present(fill):
        refuse_fill({})
    if _present(write):
        refuse_external_write({})
