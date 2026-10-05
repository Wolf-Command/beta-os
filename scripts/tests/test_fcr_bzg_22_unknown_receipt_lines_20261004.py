#!/usr/bin/env python3
"""FCR-BZG-22 — unknown receipt lines preserved (not discarded).

Fixture text only. No live vision. Never writes catalog/content_library.sqlite.
Never touches state/bzg-daily-close/receipts/. Protected closes not updated.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

PASS = 0
FAIL = 0

KNOWN_LABEL = "Sales Total"
UNKNOWN_LABEL = "Mystery Promo Surcharge"
KNOWN_AMT = 1_000_000
UNKNOWN_AMT = 50_000


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def all_lines(doc: dict) -> list[dict]:
    out: list[dict] = []
    for sec in doc.get("sections") or []:
        out.extend(sec.get("lines") or [])
    return out


def main() -> int:
    from core.bzg_close_vision import parse_shift_receipt

    fixture = {
        "sections": [
            {
                "raw_title": "Shift Summary",
                "lines": [
                    {"raw_label": KNOWN_LABEL, "amount": KNOWN_AMT},
                    {"raw_label": UNKNOWN_LABEL, "amount": UNKNOWN_AMT},
                ],
            }
        ],
    }
    fixture_text = json.dumps(fixture)

    doc = parse_shift_receipt(fixture_text)
    check("document parsed", isinstance(doc, dict) and bool(doc.get("sections")))
    check("unknown_preserved flag", doc.get("unknown_preserved") is True)

    lines = all_lines(doc)
    unknown = [ln for ln in lines if ln.get("raw_label") == UNKNOWN_LABEL]
    known = [ln for ln in lines if ln.get("raw_label") == KNOWN_LABEL]

    check("unknown line still present", len(unknown) == 1, f"count={len(unknown)}")
    if unknown:
        u = unknown[0]
        check("unknown raw label preserved", u.get("raw_label") == UNKNOWN_LABEL)
        check("unknown amount preserved", u.get("amount") == float(UNKNOWN_AMT))
        check(
            "unknown classified NEEDS_CLASSIFICATION",
            u.get("classification") == "NEEDS_CLASSIFICATION",
        )
        check("unknown normalized_type not a known total", u.get("normalized_type") == "UNKNOWN")

    check("known line still present", len(known) == 1, f"count={len(known)}")
    if known:
        k = known[0]
        check("known line classified KNOWN", k.get("classification") == "KNOWN")
        check("known line is SALES_TOTAL", k.get("normalized_type") == "SALES_TOTAL")
        check("known amount unchanged", k.get("amount") == float(KNOWN_AMT))

    shift = (doc.get("derived") or {}).get("shift") or {}
    check(
        "known total not replaced by unknown",
        shift.get("SALES_TOTAL") == float(KNOWN_AMT)
        and shift.get("SALES_TOTAL") != float(UNKNOWN_AMT),
        str(shift),
    )
    check(
        "unknown not folded into shift derived totals",
        "UNKNOWN" not in shift and UNKNOWN_AMT not in shift.values(),
        str(shift),
    )

    unclassified = (doc.get("derived") or {}).get("unclassified_lines") or []
    check(
        "unclassified_lines lists unknown label",
        any(ln.get("raw_label") == UNKNOWN_LABEL for ln in unclassified),
        str(unclassified),
    )

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
