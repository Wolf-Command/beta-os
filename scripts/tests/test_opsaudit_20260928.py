#!/usr/bin/env python3
"""OPSAUDIT-1. The audit files are complete, classified, and free of secrets.

Does not mark staff_ready or human_commissioned. Does not call Beta.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "state" / "ops" / "testability-matrix.json"
ROUTES = ROOT / "state" / "ops" / "route-audit.json"
CLASSES = {
    "WORKING",
    "WORKING BUT NOT COMMISSIONED",
    "REAL DATA NOT WIRED",
    "EXISTING IMPLEMENTATION NOT MOUNTED",
    "BROKEN",
    "BLOCKED BY EXTERNAL DEPENDENCY",
    "NOT YET BUILT",
}
MATRIX_KEYS = {
    "surface",
    "route",
    "real_data",
    "core_actions",
    "permissions",
    "desktop",
    "phone",
    "human_tester",
    "last_human_result",
    "blocker",
    "next_repair",
    "ready_to_test_now",
    "classification",
}
ROUTE_KEYS = {"seat", "device", "route", "http_status", "classification", "evidence"}
SECRET = re.compile(
    r"(?i)(password\s*[:=]\s*\S+|bearer\s+[a-z0-9._\-]{8,}|api[_-]?key\s*[:=]\s*\S+|BEGIN (RSA |OPENSSH )?PRIVATE KEY|sk_live_)"
)

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


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        check(f"parse {path.name}", False, str(exc))
        return None


def main() -> int:
    matrix = load(MATRIX)
    routes = load(ROUTES)
    if not isinstance(matrix, dict) or not isinstance(routes, dict):
        print("RESULT: FAIL unreadable")
        return 1
    check("matrix not staff ready", matrix.get("staff_ready") is False)
    check("matrix not commissioned", matrix.get("human_commissioned") is False)
    check("routes not staff ready", routes.get("staff_ready") is False)
    check("routes not commissioned", routes.get("human_commissioned") is False)
    surfaces = matrix.get("surfaces")
    check("matrix has surfaces", isinstance(surfaces, list) and len(surfaces) >= 20, str(type(surfaces)))
    if isinstance(surfaces, list):
        for row in surfaces:
            name = str((row or {}).get("surface"))
            check(f"matrix keys {name}", isinstance(row, dict) and MATRIX_KEYS <= set(row))
            check(
                f"matrix class {name}",
                isinstance(row, dict) and row.get("classification") in CLASSES,
                str((row or {}).get("classification")),
            )
            check(
                f"matrix ready {name}",
                isinstance(row, dict) and row.get("ready_to_test_now") in {"yes", "no"},
            )
    rows = routes.get("rows")
    check("route rows", isinstance(rows, list) and len(rows) >= 50)
    if isinstance(rows, list):
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not ROUTE_KEYS <= set(row):
                check(f"route keys {index}", False)
                continue
            if row.get("classification") not in CLASSES:
                check(f"route class {index}", False, str(row.get("classification")))
            if row.get("device") not in {"desktop", "phone"}:
                check(f"route device {index}", False, str(row.get("device")))
        check("every route row classified", all(isinstance(r, dict) and r.get("classification") in CLASSES for r in rows))
    blob = MATRIX.read_text(encoding="utf-8") + "\n" + ROUTES.read_text(encoding="utf-8")
    check("no secret literal", SECRET.search(blob) is None)
    check("no staff_ready true", '"staff_ready": true' not in blob and '"staff_ready":true' not in blob)
    check("no commissioned true", '"human_commissioned": true' not in blob)
    print(f"SUMMARY pass={PASS} fail={FAIL}")
    if FAIL:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
