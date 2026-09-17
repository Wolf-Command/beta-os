#!/usr/bin/env python3
"""Create/update a build-factory run JSON. Tooling only."""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
BF = ROOT / "state" / "build-factory"
RUNS = BF / "runs"
ACTIVE = BF / "ACTIVE"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--slice", required=False)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--approved-scope")
    ap.add_argument("--grok-plan-ref")
    ap.add_argument("--cursor-log")
    ap.add_argument("--cursor-pid", type=int)
    ap.add_argument("--child-log")
    ap.add_argument("--child-pid", type=int)
    ap.add_argument("--head-commit")
    ap.add_argument("--tests")
    ap.add_argument("--review-status")
    ap.add_argument("--finding", action="append", default=[])
    ap.add_argument("--fix-attempts", type=int)
    ap.add_argument("--blocker")
    ap.add_argument("--final-state")
    ap.add_argument("--clear-active", action="store_true")
    ap.add_argument("--activate", action="store_true")
    args = ap.parse_args()

    BF.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)

    if args.clear_active:
        if ACTIVE.exists():
            ACTIVE.unlink()
        print(json.dumps({"ok": True, "cleared": True}))
        return 0

    run_id = args.run_id or f"BF-{uuid.uuid4().hex[:12]}"
    path = RUNS / f"{run_id}.json"
    data = {}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("run_id", run_id)
    data.setdefault("findings", [])
    data.setdefault("fix_attempts", 0)
    if args.slice:
        data["slice"] = args.slice
    if args.approved_scope:
        data["approved_scope"] = args.approved_scope
    data["stage"] = args.stage
    if args.grok_plan_ref:
        data["grok_plan_ref"] = args.grok_plan_ref
    if args.cursor_log:
        data["cursor_log"] = args.cursor_log
    if args.cursor_pid is not None:
        data["cursor_pid"] = args.cursor_pid
    if args.child_log:
        data["child_log"] = args.child_log
    if args.child_pid is not None:
        data["child_pid"] = args.child_pid
    if args.head_commit:
        data["head_commit"] = args.head_commit
    if args.tests:
        data["tests"] = args.tests
    if args.review_status:
        data["review_status"] = args.review_status
    for f in args.finding:
        data["findings"].append(f)
    if args.fix_attempts is not None:
        data["fix_attempts"] = args.fix_attempts
    if args.blocker is not None:
        data["blocker"] = args.blocker or None
    if args.final_state:
        data["final_state"] = args.final_state
    data["updated_at"] = now()
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if args.activate or not ACTIVE.exists():
        ACTIVE.write_text(run_id + "\n", encoding="utf-8")
    if data.get("final_state") in ("DONE", "BLOCKED", "FAILED"):
        if ACTIVE.exists() and ACTIVE.read_text().strip() == run_id:
            ACTIVE.unlink()
    print(json.dumps({"ok": True, "run_id": run_id, "path": str(path), "stage": data["stage"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
