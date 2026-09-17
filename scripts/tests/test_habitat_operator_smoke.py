#!/usr/bin/env python3
"""Smoke checks for Habitat human operator UI (no CF Access / no live HTTP).

Does not exercise Core APIs. Must not break test_habitat_publish_gate.py.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "dashboards" / "habitat-operator.html"

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


def main() -> int:
    check("habitat-operator.html exists", HTML.is_file(), str(HTML))
    text = HTML.read_text(encoding="utf-8") if HTML.is_file() else ""
    for needle in (
        "Habitat Operator",
        "/api/planner?brand=habitat",
        "/api/planner/submit-for-approval",
        "/api/planner/approve",
        "/api/planner/publish-gate",
        "/api/core/approvals/",
        "/api/core/me/permissions",
        "READY_TO_PUBLISH",
        "WRITE DISABLED",
        "credentials",
        "same-origin",
    ):
        check(f"contains {needle}", needle in text)
    check("no Metricool write enable", "METRICOOL_WRITE_ENABLED=true" not in text)
    check("no person spoof fields in POST bodies", "verified_person_id:" not in text)
    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
