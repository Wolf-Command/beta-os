#!/usr/bin/env python3
"""Seat ILA Global Consulting on the existing GGV external accountant role.

Beta catalog only. Refuses production. Does not post journals, pay, or file tax.
If the Beta catalog is not in this workspace, it exits without writing.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core import ggv_ila_accountant as ila  # noqa: E402
from core import identity as identity  # noqa: E402
from core import rbac as rbac  # noqa: E402

DB = ROOT / "catalog" / "content_library.sqlite"
FORBIDDEN = ("wolf-system", "/Production", "8787", "money.sqlite")


def main() -> int:
    text = str(DB.resolve()) if DB.exists() else str(DB)
    for frag in FORBIDDEN:
        if frag in text:
            print(f"REFUSE {frag}", file=sys.stderr)
            return 2
    if not DB.is_file():
        print(
            json.dumps(
                {
                    "ok": False,
                    "seated": False,
                    "reason": "catalog_absent",
                    "path": str(DB),
                    "note": "No catalog in this workspace. Nothing was written.",
                }
            )
        )
        return 0
    for module in (ila.nota, identity, rbac):
        module.CATALOG_DB = DB
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        result = ila.seat_ila(conn)
    finally:
        conn.close()
    print(json.dumps(result))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
