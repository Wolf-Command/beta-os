#!/usr/bin/env python3
"""FC-SHELL-2 — seed honest COA structure templates into BZG + GGV books.

Decision served: FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FC-SHELL-2
(extends CORE-BOOKS-1). Copies AMG COA *shape* (codes/names/types) only.
Zero journals. Zero balances. No fake sales/P&L/invoices. Beta only.
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


def main() -> int:
    now = datetime.now(TZ8).strftime("%Y-%m-%dT%H:%M:%S%z")
    amg_before = books.snapshot("ENT-AMG")
    seeded = books.seed_all_coa_templates()
    amg_after = books.snapshot("ENT-AMG")
    probe = books.prove_isolation(f"fcshell2-{now[:13]}")
    out = {
        "migration": "fc_shell2_20260929",
        "as_of_wita": now,
        "design": "amg_coa_shape_structure_only",
        "books_isolation": "SHARED_CODE_NE_SHARED_DATA",
        "coa_template_source": "ENT-AMG",
        "seeded": seeded,
        "amg_journals_before": amg_before.get("journals"),
        "amg_journals_after": amg_after.get("journals"),
        "amg_accounts_before": amg_before.get("accounts"),
        "amg_accounts_after": amg_after.get("accounts"),
        "isolation_probe": probe,
        "staff_ready": False,
        "human_commissioned": False,
        "prod_mutate": False,
        "pack": "FC-SHELL-2",
    }
    stamp = ROOT / "state" / "final-completion" / "packs" / "FC-SHELL-2-MIGRATE.json"
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    if not probe.get("isolated"):
        print("FAIL isolation probe", file=sys.stderr)
        return 1
    if amg_before.get("journals") != amg_after.get("journals"):
        print("FAIL AMG journals mutated", file=sys.stderr)
        return 1
    if amg_before.get("accounts") != amg_after.get("accounts"):
        print("FAIL AMG accounts mutated", file=sys.stderr)
        return 1
    for row in seeded:
        if row.get("journals", -1) != 0:
            print("FAIL journals non-zero", row, file=sys.stderr)
            return 1
        if int(row.get("accounts_after") or 0) < 1:
            print("FAIL no COA seeded", row, file=sys.stderr)
            return 1
        if row.get("staff_ready") or row.get("human_commissioned"):
            print("FAIL flags", row, file=sys.stderr)
            return 1
        if row.get("shell_kind") != books.COA_TEMPLATE_SHELL:
            print("FAIL shell_kind", row, file=sys.stderr)
            return 1
    print("OK FC-SHELL-2 COA templates seeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
