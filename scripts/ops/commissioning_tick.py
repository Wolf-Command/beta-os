#!/usr/bin/env python3
"""HUMANCOMM-1 — read-only live commissioning results; optional safe apply.

Decision served: Matt 29 Sep 2026 11:12 START HUMAN COMMISSIONING NOW.
Default is read-only. --apply creates missing repairs / retests only.
Never auto-verifies PASS.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BETA_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BETA_ROOT / "scripts"))

from core import universal_my_work as umw  # noqa: E402
from core import work_items as wi  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Commissioning live tick (Beta)")
    ap.add_argument("--json", action="store_true", help="Print JSON")
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Create missing repairs for FAILs and retests for fixed repairs",
    )
    ap.add_argument("--db", type=Path, default=None, help="Optional catalog path")
    args = ap.parse_args()

    conn = wi.db_connect(args.db) if args.db else None
    try:
        snap = umw.live_commissioning_results(conn=conn)
        applied = None
        if args.apply:
            applied = umw.commissioning_tick_apply(conn=conn, commit=True)
            snap = umw.live_commissioning_results(conn=conn)
        out = {**snap, "apply": applied, "auto_verify_pass": False}
        if args.json:
            print(json.dumps(out, indent=2, default=str))
        else:
            c = out.get("counts") or {}
            print(
                f"commissioning_tick as_of={out.get('as_of')} "
                f"awaiting={c.get('awaiting_verify')} "
                f"fails_no_repair={c.get('fails_without_repair')} "
                f"repairs_no_retest={c.get('repairs_fixed_without_retest')} "
                f"rows={c.get('people_capabilities')} "
                f"apply={bool(args.apply)}"
            )
            if applied:
                print(
                    f"  created repairs={len(applied.get('repairs_created') or [])} "
                    f"retests={len(applied.get('retests_created') or [])}"
                )
        return 0
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
