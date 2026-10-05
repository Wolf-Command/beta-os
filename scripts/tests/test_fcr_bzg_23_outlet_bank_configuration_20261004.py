#!/usr/bin/env python3
"""FCR-BZG-23 — Mandiri / BNI / BRI outlet bank configuration.

Temp DB only. Never writes catalog/content_library.sqlite.
Protected closes and state/bzg-daily-close/receipts/ are not touched.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

OUTLET_UMA = "BZG-UMA"
OTHER_OUTLET = "BZG-OTHER-EMPTY"
SETTLEMENT_BANKS = ("MANDIRI", "BNI", "BRI")

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


def fresh_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def bank_row_count(conn: sqlite3.Connection, outlet_id: str) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) FROM venue_close_outlet_banks WHERE outlet_id=?",
            (outlet_id,),
        ).fetchone()[0]
    )


def main() -> int:
    from core import bzg_daily_close as bzg

    conn = fresh_conn()
    try:
        bzg.ensure_schema(conn)

        empty = bzg.list_outlet_banks(OUTLET_UMA, conn=conn)
        check(
            "empty outlet NEEDS CONFIGURATION",
            empty.get("bank_config_status") == "NEEDS CONFIGURATION",
            str(empty.get("bank_config_status")),
        )
        check("empty outlet has no bank rows", len(empty.get("banks") or []) == 0)
        check("empty outlet bank_count is 0", empty.get("bank_count") == 0)

        configured = bzg.configure_outlet_settlement_banks(OUTLET_UMA, conn=conn)
        check(
            "configure marks CONFIGURED",
            configured.get("bank_config_status") == "CONFIGURED",
            str(configured.get("bank_config_status")),
        )
        check(
            "configure creates exactly three ACTIVE rows",
            configured.get("bank_count") == 3,
            str(configured.get("bank_count")),
        )
        labels = [str(x).upper() for x in (configured.get("bank_labels") or [])]
        check(
            "configure stores MANDIRI BNI BRI only",
            labels == list(SETTLEMENT_BANKS),
            str(labels),
        )
        statuses = {str(b.get("status") or "").upper() for b in configured.get("banks") or []}
        check("all configured rows ACTIVE", statuses == {"ACTIVE"}, str(statuses))
        check(
            "no EDC or QRIS labels in bank config",
            not any("EDC" in lbl or "QRIS" in lbl for lbl in labels),
            str(labels),
        )

        second = bzg.list_outlet_banks(OUTLET_UMA, conn=conn)
        check(
            "second read still CONFIGURED",
            second.get("bank_config_status") == "CONFIGURED",
            str(second.get("bank_config_status")),
        )
        check(
            "second read does not duplicate rows",
            bank_row_count(conn, OUTLET_UMA) == 3,
            str(bank_row_count(conn, OUTLET_UMA)),
        )
        check(
            "second read returns same three labels",
            [str(x).upper() for x in (second.get("bank_labels") or [])]
            == list(SETTLEMENT_BANKS),
            str(second.get("bank_labels")),
        )

        other = bzg.list_outlet_banks(OTHER_OUTLET, conn=conn)
        check(
            "other outlet not written by Uma Blu configure",
            other.get("bank_config_status") == "NEEDS CONFIGURATION",
            str(other.get("bank_config_status")),
        )
        check(
            "other outlet has zero bank rows",
            bank_row_count(conn, OTHER_OUTLET) == 0,
            str(bank_row_count(conn, OTHER_OUTLET)),
        )
    finally:
        conn.close()

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
