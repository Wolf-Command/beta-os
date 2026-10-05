#!/usr/bin/env python3
"""Rerun control-plane accepts (Phases 1–6 + harden)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
sys.path.insert(0, str(ROOT))

from wolf_intelligence import (  # noqa: E402
    accept_phase1,
    accept_phase5,
    benchmark,
    learning,
    phase2_workers,
    scan_secrets,
    shadow_compare,
    work_items,
)
from wolf_intelligence import dispatcher, events  # noqa: E402


def main() -> int:
    work_items.bootstrap()
    results = {}
    results["phase1"] = {"exit": accept_phase1.main() == 0}
    # re-import accept result file
    p1 = ROOT / "state/wolf-intelligence/audit/phase1-accept.json"
    if p1.exists():
        results["phase1"] = json.loads(p1.read_text())
    results["phase2"] = phase2_workers.accept()
    results["phase3"] = benchmark.accept()
    results["phase4"] = learning.accept()
    results["phase5"] = accept_phase5.accept()
    results["phase6"] = shadow_compare.accept()
    # harden e2e
    wi = work_items.create(title="accept_all e2e", kind="review", isolated_safe=True, tags=["accept_all"])
    out = dispatcher.dispatch(wi["id"])
    item = work_items.get(wi["id"])
    ev = events.read_events(work_item_id=wi["id"])
    results["harden_e2e"] = {
        "ok": item is not None and item["state"] in ("READY_TO_TEST", "NEEDS_YOU", "EXCEPTION") and len(ev) >= 3,
        "state": item["state"] if item else None,
        "events": len(ev),
        "store": work_items.store_info(),
        "shadow": out.get("mode") == "SHADOW",
    }
    results["secret_scan"] = scan_secrets.scan_tree()
    passed = all(
        [
            results["phase1"].get("passed", results["phase1"].get("exit")),
            results["phase2"].get("passed"),
            results["phase3"].get("passed"),
            results["phase4"].get("passed"),
            results["phase5"].get("passed"),
            results["phase6"].get("passed"),
            results["harden_e2e"]["ok"],
            results["secret_scan"]["ok"],
        ]
    )
    report = {"passed": passed, "results": results}
    path = ROOT / "state/wolf-intelligence/audit/accept-all.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": passed, "phase5_ui": results["phase5"].get("owner_ui_link"), "store": results["harden_e2e"]["store"]}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
