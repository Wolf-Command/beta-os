"""Simultaneous-completion proof harness for orchestrator CAS transitions."""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import shutil
from pathlib import Path
from typing import Any

from .paths import rebind_state_paths


def _trial_root(state_root: str, trial_idx: int) -> str:
    return str(Path(state_root) / f"trial-{trial_idx:04d}")


def _bind_state(state_root: str) -> None:
    os.environ["WOLF_INTELLIGENCE_STATE_ROOT"] = state_root
    rebind_state_paths()
    from . import orchestrator as orch

    orch.rebind_orchestrator_paths()


def _setup_running_item(state_root: str, item_id: str = "wi-race-same") -> None:
    _bind_state(state_root)
    from . import orchestrator as orch

    orch.ORCH_DIR.mkdir(parents=True, exist_ok=True)
    orch.save_config({"allow_concurrent_orchestrators": True, "worktree_cwd": state_root})
    orch.submit(
        {
            "id": item_id,
            "kind": "build",
            "spec": {"prompt": "race"},
            "acceptance": "ok",
            "reviewer_gate": False,
            "timeout_s": 5,
            "max_attempts": 1,
        },
        now="2026-10-06T12:00:00+08:00",
    )
    claimed, _ = orch.claim(item_id, now="2026-10-06T12:00:01+08:00")
    assert claimed is not None
    items = orch.load_items()
    running = dict(items[item_id])
    running["status"] = "RUNNING"
    running["version"] = int(running.get("version") or 0) + 1
    running["updated_at"] = "2026-10-06T12:00:01+08:00"
    items[item_id] = running
    orch.save_items(items)


def _mp_dual_complete(state_root: str, item_id: str, role: int, barrier: mp.synchronize.Barrier) -> None:
    _bind_state(state_root)
    from . import orchestrator as orch

    barrier.wait()
    item = orch.show(item_id)
    if not item:
        return
    orch._finish_dispatch(
        item,
        "cursor_sub",
        status="COMPLETED",
        summary=f"complete-{role}",
        exceptions=[],
        exit_code=0,
        now="2026-10-06T12:00:02+08:00",
        argv=["cursor_sub"],
        using_override=True,
    )


def _mp_complete_one(state_root: str, item_id: str, role: int, barrier: mp.synchronize.Barrier) -> None:
    _bind_state(state_root)
    from . import orchestrator as orch

    barrier.wait()
    item = orch.show(item_id)
    if item:
        orch._finish_dispatch(
            item,
            "cursor_sub",
            status="COMPLETED",
            summary=f"complete-{item_id}",
            exceptions=[],
            exit_code=0,
            now="2026-10-06T12:00:02+08:00",
            argv=["cursor_sub"],
            using_override=True,
        )


def _mp_complete_vs_claim(state_root: str, item_id: str, role: int, barrier: mp.synchronize.Barrier) -> None:
    _bind_state(state_root)
    from . import orchestrator as orch

    barrier.wait()
    if role == 0:
        item = orch.show(item_id)
        if item:
            orch._finish_dispatch(
                item,
                "cursor_sub",
                status="COMPLETED",
                summary="complete",
                exceptions=[],
                exit_code=0,
                now="2026-10-06T12:00:02+08:00",
                argv=["cursor_sub"],
                using_override=True,
            )
    else:
        orch.claim(item_id, now="2026-10-06T12:00:02+08:00")


def _audit_complete_events(state_root: str, item_id: str) -> list[dict[str, Any]]:
    _bind_state(state_root)
    from . import orchestrator as orch

    events: list[dict[str, Any]] = []
    if not orch.AUDIT_PATH.exists():
        return events
    for line in orch.AUDIT_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("work_item_id") == item_id and rec.get("event") == "complete":
            events.append(rec)
    return events


def _validate_trial(state_root: str, item_ids: list[str]) -> dict[str, int]:
    _bind_state(state_root)
    from . import orchestrator as orch

    counters = {
        "lost_events": 0,
        "duplicate_advances": 0,
        "stuck_items": 0,
        "invalid_transitions": 0,
    }
    for item_id in item_ids:
        item = orch.show(item_id)
        if not item:
            counters["lost_events"] += 1
            continue
        status = item.get("status")
        version = int(item.get("version") or 0)
        completes = _audit_complete_events(state_root, item_id)
        successful = [e for e in completes if (e.get("after") or {}).get("status") in ("CLOSED", "AWAITING_REVIEW")]
        if len(successful) > 1:
            counters["duplicate_advances"] += len(successful) - 1
        if len(successful) == 0 and status in ("RUNNING", "CLAIMED"):
            counters["stuck_items"] += 1
        if status == "CLAIMED" and version > 2:
            counters["invalid_transitions"] += 1
        if status == "CLOSED" and any(
            (e.get("before") or {}).get("status") == "CLOSED" and (e.get("after") or {}).get("status") != "CLOSED"
            for e in completes
        ):
            counters["invalid_transitions"] += 1
        if status in ("CLOSED", "AWAITING_REVIEW") and len(successful) != 1:
            counters["lost_events"] += abs(1 - len(successful))
    return counters


def _run_scenario(
    scenario: str,
    state_root: str,
    *,
    ctx: mp.context.BaseContext,
) -> dict[str, int]:
    root = Path(state_root)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    if scenario == "same_item_dual_complete":
        _setup_running_item(state_root, "wi-race-same")
        barrier = ctx.Barrier(2)
        procs = [
            ctx.Process(target=_mp_dual_complete, args=(state_root, "wi-race-same", i, barrier))
            for i in range(2)
        ]
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=30)
        return _validate_trial(state_root, ["wi-race-same"])

    if scenario == "different_items_dual_complete":
        _setup_running_item(state_root, "wi-race-a")
        _setup_running_item(state_root, "wi-race-b")
        barrier = ctx.Barrier(2)
        procs = [
            ctx.Process(target=_mp_complete_one, args=(state_root, "wi-race-a", 0, barrier)),
            ctx.Process(target=_mp_complete_one, args=(state_root, "wi-race-b", 1, barrier)),
        ]
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=30)
        return _validate_trial(state_root, ["wi-race-a", "wi-race-b"])

    if scenario == "complete_vs_claim":
        _setup_running_item(state_root, "wi-race-x")
        barrier = ctx.Barrier(2)
        procs = [
            ctx.Process(target=_mp_complete_vs_claim, args=(state_root, "wi-race-x", i, barrier))
            for i in range(2)
        ]
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=30)
        return _validate_trial(state_root, ["wi-race-x"])

    return {"lost_events": 1, "duplicate_advances": 0, "stuck_items": 0, "invalid_transitions": 1}


SCENARIOS = (
    "same_item_dual_complete",
    "different_items_dual_complete",
    "complete_vs_claim",
)


def run_race_proof(
    trials: int = 250,
    state_root: str = ".tmp/race-proof",
    out_file: str | None = None,
) -> dict[str, Any]:
    root = Path(state_root)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    totals = {
        "lost_events": 0,
        "duplicate_advances": 0,
        "stuck_items": 0,
        "invalid_transitions": 0,
    }
    per_scenario: dict[str, dict[str, int]] = {s: dict(totals) for s in SCENARIOS}
    ctx = mp.get_context("spawn")

    for trial in range(trials):
        for scenario in SCENARIOS:
            trial_dir = _trial_root(state_root, trial) + f"-{scenario}"
            counts = _run_scenario(scenario, trial_dir, ctx=ctx)
            for key in totals:
                totals[key] += counts[key]
                per_scenario[scenario][key] += counts[key]

    result: dict[str, Any] = {
        "trials": trials,
        "lost_events": totals["lost_events"],
        "duplicate_advances": totals["duplicate_advances"],
        "stuck_items": totals["stuck_items"],
        "invalid_transitions": totals["invalid_transitions"],
        "per_scenario": per_scenario,
        "pass": all(v == 0 for v in totals.values()),
    }
    if out_file:
        out_path = Path(out_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
