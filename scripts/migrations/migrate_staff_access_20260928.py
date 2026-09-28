#!/usr/bin/env python3
"""Register staff identities on the Beta catalog. Not a test. Not production."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from core.identity import db_connect  # noqa: E402
from core.staff_access import apply  # noqa: E402


def main() -> None:
    conn = db_connect()
    try:
        report = apply(conn)
    finally:
        conn.close()
    print(json.dumps({k: v for k, v in report.items() if k != "finance"}))
    finance = report["finance"]
    print(
        "finance_bound",
        finance["bound"],
        "person_by_email",
        finance["person_by_email"],
        "name_matches",
        len(finance["name_matches"]),
    )


if __name__ == "__main__":
    main()
