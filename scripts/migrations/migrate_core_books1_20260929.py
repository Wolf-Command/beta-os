#!/usr/bin/env python3
"""CORE-BOOKS-1 — open BZG + GGV books shells (separate SQLite files).

Decision served: Matt-ordered Owner sprint CORE-BOOKS-1 (2026-09-29).
Inventory: state/finance-core-sprint/INVENTORY-20260929.json.

Creates atrium-bzg.sqlite + atrium-ggv.sqlite under atrium-finance/data/beta/.
Stamps books_slot_meta on AMG atrium.sqlite without wiping journals.
Does not invent money. Does not flip staff_ready / human_commissioned.
Beta only. No prod.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core import entity_books as books  # noqa: E402

TZ8 = timezone(timedelta(hours=8))
FORBIDDEN = ("8787", "/Production", "staff_ready=true", "human_commissioned=true")


def main() -> int:
    now = datetime.now(TZ8).strftime("%Y-%m-%dT%H:%M:%S%z")
    results = books.ensure_all_shells()
    probe = books.prove_isolation(f"corebooks1-{now[:13]}")
    out = {
        "migration": "core_books1_20260929",
        "as_of_wita": now,
        "design": "separate_sqlite_files",
        "books_isolation": "SHARED_CODE_NE_SHARED_DATA",
        "entities": results,
        "isolation_probe": probe,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_mutate": False,
    }
    stamp = ROOT / "state" / "finance-core-sprint" / "CORE-BOOKS-1-ARM.json"
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    if not probe.get("isolated"):
        print("FAIL isolation probe", file=sys.stderr)
        return 1
    for row in results:
        if not row.get("books_enabled"):
            print("FAIL books_enabled", row, file=sys.stderr)
            return 1
        if row["legal_entity_id"] != "ENT-AMG" and row.get("journals", 0) != 0:
            print("FAIL non-empty shell", row, file=sys.stderr)
            return 1
        if row.get("staff_ready") or row.get("human_commissioned"):
            print("FAIL flags", row, file=sys.stderr)
            return 1
    amg = next(r for r in results if r["legal_entity_id"] == "ENT-AMG")
    if amg.get("journals", 0) < 1:
        print("WARN AMG journals unexpectedly empty", amg, file=sys.stderr)
    print("OK CORE-BOOKS-1 shells ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
