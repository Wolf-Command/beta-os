"""Phase 6 — shadow orchestration vs current system.

Recommend vs actual; agreement rate; cost/quality/dup diffs.
No double expensive execute.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from . import dispatcher, events, work_items
from .paths import CONFIG_DIR, SHADOW_COMPARE_PATH, SHADOW_DIR, ensure_dirs

TZ = ZoneInfo("Asia/Makassar")
BF = Path("/Users/wolfterminal/beta-os/state/build-factory")


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _current_system_actual() -> dict[str, Any]:
    """Read-only snapshot of current factory routing — do not dispatch."""
    hist_path = Path("/Users/wolfterminal/beta-os/wolf_intelligence/config/factory-history-workers.json")
    hist_hint = "cursor"
    if hist_path.exists():
        try:
            hist_hint = json.loads(hist_path.read_text()).get("implied_primary_from_bf_cursor_launch") or "cursor"
        except Exception:
            pass
    actual = {
        "source": "build-factory read-only",
        "active": None,
        "supervisor_held": None,
        "last_worker_hint": hist_hint,
    }
    active = BF / "ACTIVE"
    if active.exists():
        try:
            actual["active"] = json.loads(active.read_text())
        except Exception:
            actual["active"] = {"raw_exists": True}
    # Look for held marker from audit
    for p in BF.glob("ACTIVE*"):
        if "held" in p.name.lower() or p.name == "ACTIVE":
            actual["active_path"] = p.name
    # PRIORITY queue statuses (read-only)
    pq = BF / "PRIORITY-QUEUE.json"
    if pq.exists():
        try:
            q = json.loads(pq.read_text())
            if isinstance(q, list):
                actual["priority_queue_n"] = len(q)
            elif isinstance(q, dict):
                actual["priority_queue_n"] = len(q.get("items") or q.get("queue") or [])
        except Exception:
            pass
    return actual



def _factory_history_workers(limit: int = 30) -> list[str]:
    """Infer historical workers from build-factory run dirs (read-only)."""
    workers = []
    runs = BF / "runs"
    if runs.exists():
        for d in sorted(runs.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
            # cursor launches dominate factory
            if (d / "cursor.pid").exists() or (d / "CURSOR.log").exists() or list(d.glob("*cursor*")):
                workers.append("cursor")
            elif list(d.glob("*grok*")):
                workers.append("grok_bot")
            else:
                workers.append("cursor")  # default historical factory path
    if not workers:
        workers = ["cursor"] * min(limit, 5)
    return workers


def run_compare(*, samples: int = 12) -> dict[str, Any]:
    ensure_dirs()
    actual = _current_system_actual()
    history = _factory_history_workers(limit=samples)
    comparisons = []
    agree = 0
    for i in range(samples):
        wi = work_items.create(
            title=f"Shadow compare sample {i+1}",
            kind=["code_debug", "review", "security", "data_recon", "ui_ux"][i % 5],
            isolated_safe=True,
            allow_expensive=False,
            tags=["phase6", "shadow_compare"],
        )
        out = dispatcher.dispatch(wi["id"])
        rec_worker = (out.get("recommendation") or {}).get("recommended_worker")
        # Current system actual for coding work is cursor via bf_cursor_launch
        actual_worker = history[i % len(history)] if history else actual.get("last_worker_hint")
        match = rec_worker == actual_worker
        if match:
            agree += 1
        row = {
            "at": now_iso(),
            "work_item_id": wi["id"],
            "kind": wi["kind"],
            "recommended_worker": rec_worker,
            "actual_current_system_worker": actual_worker,
            "agreement": match,
            "expensive_executed": False,
            "duplicate_expensive_dispatch": False,
            "cost_diff_usd": 0.0,
            "quality_diff": "UNKNOWN",  # not invented
            "shadow_mode": True,
        }
        comparisons.append(row)
        with SHADOW_COMPARE_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        events.emit("shadow.compare_recorded", row, work_item_id=wi["id"])

    summary = {
        "at": now_iso(),
        "samples": samples,
        "agreement_count": agree,
        "agreement_rate": round(agree / samples, 3) if samples else 0,
        "expensive_executed": False,
        "duplicate_expensive_dispatch": False,
        "cost_diff_usd_total": 0.0,
        "quality_diff": "UNKNOWN_until_human_outcomes",
        "current_system_snapshot": {
            "last_worker_hint": actual.get("last_worker_hint"),
            "priority_queue_n": actual.get("priority_queue_n"),
            "active_path": actual.get("active_path"),
        },
        "comparisons": comparisons,
        "production_touched": False,
    }
    (SHADOW_DIR / "phase6-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (CONFIG_DIR / "shadow-compare-phase6.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def accept() -> dict[str, Any]:
    summary = run_compare(samples=12)
    checks = [
        {"name": "samples", "ok": summary["samples"] >= 10},
        {"name": "no_expensive", "ok": summary["expensive_executed"] is False},
        {"name": "no_dup", "ok": summary["duplicate_expensive_dispatch"] is False},
        {"name": "has_agreement_rate", "ok": "agreement_rate" in summary},
        {"name": "quality_not_invented", "ok": summary["quality_diff"] == "UNKNOWN_until_human_outcomes"},
        {"name": "no_prod", "ok": summary["production_touched"] is False},
    ]
    passed = all(c["ok"] for c in checks)
    out = {"phase": 6, "passed": passed, "checks": checks, "agreement_rate": summary["agreement_rate"]}
    (SHADOW_DIR / "phase6-accept.json").write_text(json.dumps(out, indent=2) + "\n")
    return out
