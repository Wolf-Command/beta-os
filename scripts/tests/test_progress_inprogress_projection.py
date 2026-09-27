#!/usr/bin/env python3
"""P0 Progress In progress projection — factory lanes must not silent-zero.

Decision: 2026-09-17 · PICK Matt Progress Dashboard (Beta).
Plan: docs/deliveries/GROK-PLAN-P0-PROGRESS-INPROGRESS-PROJECTION-2026-09-22.md

Does not invent SYSTEM%. Does not write Production / Habitat / ESB.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core import completion_register as cr  # noqa: E402
from core import progress_read_model as prm  # noqa: E402

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


def _write_run(runs: Path, run_id: str, stage: str, **extra: object) -> None:
    payload = {
        "run_id": run_id,
        "slice": extra.pop("slice", run_id),
        "stage": stage,
        "updated_at": extra.pop("updated_at", "2026-09-22T01:00:00Z"),
        **extra,
    }
    (runs / f"{run_id}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def test_active_factory_not_zero() -> None:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        factory = base / "build-factory"
        runs = factory / "runs"
        runs.mkdir(parents=True)
        _write_run(
            runs,
            "BF-fixture-active-20260922",
            "ACTIVE",
            slice="fixture-active-pack",
            updated_at="2026-09-22T02:00:00Z",
        )
        _write_run(
            runs,
            "BF-fixture-done-20260922",
            "DONE",
            slice="fixture-done-pack",
            updated_at="2026-09-22T01:30:00Z",
        )
        (factory / "ACTIVE").write_text(
            "BF-fixture-active-20260922\n", encoding="utf-8"
        )
        (factory / "IDLE-REASON.json").write_text(
            json.dumps(
                {
                    "reason": "fixture",
                    "active_run": "BF-fixture-active-20260922",
                    "parked": ["Devi", "P1"],
                }
            ),
            encoding="utf-8",
        )
        (factory / "COMPRESSED-SPRINT-2-ARMED.json").write_text(
            json.dumps({"no_wait_devi": True, "no_wait_habitat": True}),
            encoding="utf-8",
        )
        (factory / "supervisor-ticks.jsonl").write_text(
            json.dumps(
                {
                    "at": "2026-09-22T02:05:00Z",
                    "action": "CONTINUE_CURSOR",
                    "run_id": "BF-fixture-active-20260922",
                    "stage": "ACTIVE",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        db = base / "register.sqlite"
        conn = cr.db_connect(db)
        try:
            # Register has OPEN debt but zero IN_PROGRESS — the silent-zero bug case.
            cr.upsert(
                conn,
                item_type="EXPLICIT",
                title="Fixture open debt",
                entity="SHARED",
                state="OPEN",
                blocker_class="NEEDS_ENGINEERING",
                domain="Core",
                view_key="Empire",
                why_it_matters="fixture",
                source="fixture",
            )
            summary = cr.summary_for_owner(conn)
            check("register alone in_progress is 0", summary["in_progress"] == 0)

            surface = prm.factory_work_surface(
                factory_root=factory, runs_dir=runs
            )
            check("factory surface in_flight ≥ 1", surface["in_flight_count"] >= 1)
            check(
                "current active pack set",
                (surface.get("current_active_pack") or {}).get("run_id")
                == "BF-fixture-active-20260922",
            )
            check(
                "recently completed present",
                any(
                    c.get("run_id") == "BF-fixture-done-20260922"
                    for c in (surface.get("recently_completed") or [])
                ),
            )
            branches = {
                str(b.get("branch") or "").lower()
                for b in (surface.get("blocked_human_branches") or [])
            }
            check("Devi blocked branch surfaced", any("devi" in b for b in branches))
            check(
                "Habitat blocked branch surfaced",
                any("habitat" in b for b in branches),
            )
            check(
                "last factory advance present",
                (surface.get("last_factory_advance") or {}).get("at")
                == "2026-09-22T02:05:00Z",
            )

            projected = prm.project_open_loops_with_factory(summary, surface)
            check(
                "ACTIVE factory → In progress not 0",
                int(projected.get("in_progress") or 0) >= 1,
                str(projected.get("in_progress")),
            )
            check(
                "projection not stale when factory counted",
                projected.get("projection_stale") is False,
            )
            check(
                "factory_work on open_loops",
                isinstance(projected.get("factory_work"), dict)
                and (projected["factory_work"].get("in_flight_count") or 0) >= 1,
            )

            model = prm.build_read_model(
                register_db_path=db,
                factory_root=factory,
                factory_runs_dir=runs,
            )
            loops = model.get("open_loops") or {}
            check(
                "build_read_model In progress ≥ 1",
                int(loops.get("in_progress") or 0) >= 1,
                str(loops.get("in_progress")),
            )
            check(
                "SYSTEM% untouched path present",
                (model.get("system") or {}).get("system_pct") is not None
                or (model.get("system") or {}).get("status") == prm.STALE_STATUS
                or "system_pct" in (model.get("system") or {}),
            )
            # Must not invent a second scoring table — system still ledger path
            check(
                "progress_type still SYSTEM_FROM_LEDGER",
                model.get("progress_type") == "SYSTEM_FROM_LEDGER",
            )
        finally:
            conn.close()


def test_empty_factory_honest_zero() -> None:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        factory = base / "build-factory"
        runs = factory / "runs"
        runs.mkdir(parents=True)
        # Empty runs dir — honest zero, no stale lie.
        db = base / "register.sqlite"
        conn = cr.db_connect(db)
        try:
            summary = cr.summary_for_owner(conn)
            surface = prm.factory_work_surface(
                factory_root=factory, runs_dir=runs
            )
            check("empty factory in_flight 0", surface["in_flight_count"] == 0)
            projected = prm.project_open_loops_with_factory(summary, surface)
            check(
                "empty factory → In progress 0",
                int(projected.get("in_progress") or 0) == 0,
            )
            check(
                "empty factory → no projection stale lie",
                projected.get("projection_stale") is False,
            )
            check(
                "empty factory current active none",
                projected.get("factory_work", {}).get("current_active_pack") is None,
            )
        finally:
            conn.close()


def test_html_markers() -> None:
    html = (ROOT / "dashboards" / "progress.html").read_text(encoding="utf-8")
    check("HTML factory-work section", 'data-section="factory-work"' in html)
    check("HTML PROJECTION STALE branch", "PROJECTION STALE" in html)
    check("HTML Current active label", "Current active" in html)
    check("HTML Blocked human branches", "Blocked human branches" in html)
    check(
        "HTML does not hard-code In progress 0",
        "In progress <strong>0" not in html,
    )


def test_live_beta_projection() -> None:
    """Live Beta read: if factory has in-flight, In progress must not be 0."""
    surface = prm.factory_work_surface()
    fac_ip = int(surface.get("in_flight_count") or 0)
    loops = prm.open_loops_summary()
    ip = int(loops.get("in_progress") or 0)
    if fac_ip > 0:
        check(
            "live factory in-flight → In progress ≥ 1",
            ip >= 1,
            f"factory_in_flight={fac_ip} in_progress={ip}",
        )
        check(
            "live projection not silently stale",
            loops.get("projection_stale") is False or ip >= 1,
        )
    else:
        check("live factory empty — skip ≥1 assert", True)
    check("live factory_work attached", "factory_work" in loops)
    # SYSTEM% must remain a ledger projection field (may be OK or STALE independently)
    model = prm.build_read_model()
    system = model.get("system") or {}
    check(
        "live SYSTEM not invented by this fix",
        system.get("progress_type") in (None, "SYSTEM_FROM_LEDGER")
        or model.get("progress_type") == "SYSTEM_FROM_LEDGER",
    )


def main() -> int:
    test_active_factory_not_zero()
    test_empty_factory_honest_zero()
    test_html_markers()
    test_live_beta_projection()
    print(f"PASS={PASS} FAIL={FAIL}")
    if FAIL:
        print("EXIT: FAILED")
        return 1
    print("EXIT: SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
