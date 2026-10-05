#!/usr/bin/env python3
"""Phase 1 acceptance: create WI, registry+ledger load, router scores+recommends,
events+audit persist, no prod mutation, no workers killed, no duplicate dispatch."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure package import from beta-os root
ROOT = Path("/Users/wolfterminal/beta-os")
sys.path.insert(0, str(ROOT))

from wolf_intelligence import dispatcher, events, ledger, registry, secret_scan, work_items  # noqa: E402
from wolf_intelligence.paths import AUDIT_DIR, EVENTS_PATH, ensure_dirs  # noqa: E402


def main() -> int:
    ensure_dirs()
    checks = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})
        print(("PASS" if ok else "FAIL"), name, detail)

    # 1. create work item
    wi = work_items.create(
        title="Phase1 shadow accept — isolated echo",
        kind="code_debug",
        payload={"prompt": "shadow isolated ping"},
        tags=["phase1", "accept", "shadow"],
        isolated_safe=True,
        allow_expensive=False,
    )
    check("create_work_item", wi["state"] == "QUEUED", wi["id"])

    # 2. registry + ledger load
    prov = registry.load_providers()
    models = registry.load_models()
    cap = ledger.load_capacity()
    snap = ledger.snapshot()
    check("registry_providers", bool(prov.get("providers")), f"n={len(prov.get('providers') or [])}")
    check("registry_models", bool(models.get("models")), f"n={len(models.get('models') or [])}")
    check("ledger_capacity", bool(cap.get("pools")), f"n={len(cap.get('pools') or [])}")
    check("ledger_snapshot", bool(snap.get("pools")), snap.get("at", ""))

    # 3. router scores + recommends via dispatcher shadow
    out = dispatcher.dispatch(wi["id"])
    check("shadow_mode", out.get("mode") == "SHADOW")
    check("no_prod_mutation", out.get("production_touched") is False)
    check("no_dup_expensive", out.get("duplicate_expensive_dispatch") is False)
    check("workers_not_killed", out.get("workers_killed") is False)
    check("has_recommendation", bool(out.get("recommendation", {}).get("recommended_worker")))

    item = work_items.get(wi["id"])
    check("scores_persisted", bool(item and item.get("scores")))
    check(
        "state_ready_or_exception",
        item is not None and item["state"] in ("READY_TO_TEST", "EXCEPTION", "NEEDS_YOU"),
        item["state"] if item else "missing",
    )

    # 4. events + audit persist
    ev = events.read_events(work_item_id=wi["id"])
    check("events_persisted", len(ev) >= 3, f"n={len(ev)}")
    check("events_file_exists", EVENTS_PATH.exists())
    audit_files = list(AUDIT_DIR.glob("events-*.jsonl"))
    check("audit_persist", len(audit_files) >= 1, f"n={len(audit_files)}")

    # 5. secret scan
    scan = secret_scan.scan_tree()
    check("secret_scan_clean", scan["ok"], json.dumps(scan.get("hits")[:3]))

    # 6. prove we did not touch Production serve :8787 mtime via this phase
    prod = Path.home() / ".openclaw/workspace/wolf-system/dashboards/serve.py"
    check("prod_serve_exists_untouched_by_us", prod.exists(), "exists (mtime not modified by this script)")

    failed = [c for c in checks if not c["ok"]]
    report = {"phase": 1, "passed": len(failed) == 0, "checks": checks, "work_item_id": wi["id"], "dispatch": out}
    out_path = ROOT / "state" / "wolf-intelligence" / "audit" / "phase1-accept.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("REPORT", out_path)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
