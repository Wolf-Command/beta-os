"""Phase 4 — learning loop from outcomes. Human judgment > self-eval."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from . import events, work_items
from .paths import LEARNING_DIR, ensure_dirs

TZ = ZoneInfo("Asia/Makassar")
OUTCOMES_PATH = LEARNING_DIR / "outcomes.jsonl"
WEIGHTS_PATH = LEARNING_DIR / "weights.json"


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def record_outcome(
    work_item_id: str,
    *,
    human_passed: bool | None = None,
    human_rating: int | None = None,
    self_eval_rating: int | None = None,
    notes: str = "",
    model_id: str | None = None,
    worker_id: str | None = None,
) -> dict[str, Any]:
    """Human fields dominate. Self-eval stored but never overrides human."""
    ensure_dirs()
    item = work_items.get(work_item_id)
    rec = {
        "at": now_iso(),
        "work_item_id": work_item_id,
        "model_id": model_id or ((item or {}).get("recommendation") or {}).get("recommended_model_id"),
        "worker_id": worker_id or ((item or {}).get("recommendation") or {}).get("recommended_worker"),
        "human_passed": human_passed,
        "human_rating": human_rating,
        "self_eval_rating": self_eval_rating,
        "human_dominates": True,
        "notes": notes,
    }
    # Effective score: human if present else UNKNOWN (not self-eval)
    if human_rating is not None:
        rec["effective_rating"] = human_rating
        rec["effective_source"] = "human"
    elif human_passed is not None:
        rec["effective_rating"] = 5 if human_passed else 1
        rec["effective_source"] = "human_passed_bool"
    else:
        rec["effective_rating"] = None
        rec["effective_source"] = "UNKNOWN_pending_human"
        # self-eval may be stored for later comparison only
        rec["self_eval_only"] = self_eval_rating
    with OUTCOMES_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    events.emit("outcome.recorded", rec, work_item_id=work_item_id)
    if human_passed is not None or human_rating is not None:
        events.emit("outcome.human_override", {"dominates_self_eval": True}, work_item_id=work_item_id)
    _recompute_weights()
    if item:
        outs = list(item.get("outcomes") or [])
        outs.append(rec)
        work_items.update_fields(work_item_id, outcomes=outs)
        if human_passed is True and item.get("state") == "READY_TO_TEST":
            work_items.transition(work_item_id, "HUMAN_PASSED", reason="human learning outcome")
        elif human_passed is False and item.get("state") in ("READY_TO_TEST", "NEEDS_YOU"):
            work_items.transition(work_item_id, "BLOCKED", reason="human failed outcome")
    return rec


def _recompute_weights() -> dict[str, Any]:
    ensure_dirs()
    tallies: dict[str, dict[str, Any]] = {}
    if OUTCOMES_PATH.exists():
        with OUTCOMES_PATH.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("effective_source") in (None, "UNKNOWN_pending_human"):
                    continue
                key = rec.get("model_id") or rec.get("worker_id") or "unknown"
                t = tallies.setdefault(key, {"n_human": 0, "sum_rating": 0.0, "passes": 0, "fails": 0})
                t["n_human"] += 1
                if rec.get("effective_rating") is not None:
                    t["sum_rating"] += float(rec["effective_rating"])
                if rec.get("human_passed") is True:
                    t["passes"] += 1
                elif rec.get("human_passed") is False:
                    t["fails"] += 1
    weights = {"updated_at": now_iso(), "rule": "human > self-eval", "models": {}}
    for key, t in tallies.items():
        avg = (t["sum_rating"] / t["n_human"]) if t["n_human"] else None
        weights["models"][key] = {
            **t,
            "avg_human_rating": avg,
            "self_eval_weight": 0.0,  # never drives routing alone
            "human_weight": 1.0,
        }
    WEIGHTS_PATH.write_text(json.dumps(weights, indent=2) + "\n", encoding="utf-8")
    events.emit("learning.updated", {"models": list(weights["models"].keys())})
    return weights


def demo_cycle() -> dict[str, Any]:
    """Acceptance demo: create WI-like outcome path without expensive dispatch."""
    ensure_dirs()
    wi = work_items.create(
        title="Phase4 learning demo",
        kind="review",
        isolated_safe=True,
        tags=["phase4", "learning"],
    )
    # Simulate recommendation already done
    work_items.update_fields(
        wi["id"],
        recommendation={
            "recommended_model_id": "cursor-agent",
            "recommended_worker": "cursor",
            "mode": "SHADOW",
        },
    )
    work_items.transition(wi["id"], "ROUTING", reason="learning demo")
    work_items.transition(wi["id"], "RECOMMENDED", reason="learning demo")
    work_items.transition(wi["id"], "DISPATCHED_SHADOW", reason="learning demo")
    work_items.transition(wi["id"], "RUNNING", reason="learning demo")
    work_items.transition(wi["id"], "READY_TO_TEST", reason="learning demo")
    # Self-eval alone must NOT pass
    self_only = record_outcome(wi["id"], self_eval_rating=5, notes="self-eval only")
    assert self_only["effective_source"] == "UNKNOWN_pending_human"
    # Human dominates
    human = record_outcome(wi["id"], human_passed=True, human_rating=4, self_eval_rating=5, notes="human wins")
    item = work_items.get(wi["id"])
    weights = json.loads(WEIGHTS_PATH.read_text()) if WEIGHTS_PATH.exists() else {}
    return {
        "work_item_id": wi["id"],
        "final_state": item["state"] if item else None,
        "self_only_source": self_only["effective_source"],
        "human_source": human["effective_source"],
        "human_dominates": human["human_dominates"],
        "weights_has_cursor": "cursor-agent" in (weights.get("models") or {}),
    }


def accept() -> dict[str, Any]:
    demo = demo_cycle()
    checks = [
        {"name": "self_eval_not_effective", "ok": demo["self_only_source"] == "UNKNOWN_pending_human"},
        {"name": "human_effective", "ok": demo["human_source"].startswith("human")},
        {"name": "human_passed_state", "ok": demo["final_state"] == "HUMAN_PASSED"},
        {"name": "weights_updated", "ok": demo["weights_has_cursor"]},
    ]
    passed = all(c["ok"] for c in checks)
    out = {"phase": 4, "passed": passed, "checks": checks, "demo": demo}
    (LEARNING_DIR / "phase4-accept.json").write_text(json.dumps(out, indent=2) + "\n")
    return out
