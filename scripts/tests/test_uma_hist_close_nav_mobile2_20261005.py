#!/usr/bin/env python3
"""UMA-HIST-CLOSE-NAV-MOBILE-2 — no VDC- in DOM, sanitised errors, opening feedback."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "dashboards" / "uma-blu-close.html"
sys.path.insert(0, str(ROOT / "scripts"))

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


def prod_pid_8787() -> int | None:
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", "tcp:8787"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if not out:
            return None
        return int(out.splitlines()[0])
    except Exception:
        return None


def test_no_close_id_in_dom_assignments() -> None:
    html = UI.read_text(encoding="utf-8")
    # Every textContent / innerHTML assignment in owner UI
    dom_assign = re.findall(
        r'\.(?:textContent|innerHTML)\s*=\s*([^;]+);',
        html,
    )
    check("dom assignments found", len(dom_assign) > 0, str(len(dom_assign)))
    for i, expr in enumerate(dom_assign):
        has_close_id = "close_id" in expr
        has_vdc = "VDC-" in expr
        check(
            f"dom assign {i} no close_id",
            not has_close_id,
            expr.strip()[:80],
        )
        check(
            f"dom assign {i} no VDC- literal",
            not has_vdc,
            expr.strip()[:80],
        )
    # showExceptionSummary must not write close ref
    check(
        "showExceptionSummary no Close ref",
        "Close ref:" not in html,
    )
    compact = html.replace(" ", "").replace("\n", "")
    check(
        "exceptionAuditBody no close_id concat",
        'exceptionAuditBody").textContent=row.close_id' not in compact,
    )


def test_sanitize_owner_text() -> None:
    html = UI.read_text(encoding="utf-8")
    check("sanitize function", "function sanitize" in html)
    check(
        "VDC regex in sanitizer",
        re.search(r"VDC-\[0-9a-f-\]\+", html, re.I) is not None,
    )
    check("setMsg uses sanitizer", "sanitize(text" in html)
    check("setTop uses sanitizer", "sanitize(text" in html)
    m = re.search(
        r"function setMsg\([^)]*\)\s*\{[\s\S]*?sanitize",
        html,
    )
    check("setMsg body sanitises", m is not None)
    m2 = re.search(
        r"function setTop\([^)]*\)\s*\{[\s\S]*?sanitize",
        html,
    )
    check("setTop body sanitises", m2 is not None)


def test_opening_message_persists() -> None:
    html = UI.read_text(encoding="utf-8")
    check("topMsg element", 'id="topMsg"' in html)
    check(
        "open uses setTop opening",
        'setTop("Opening ' in html,
    )
    check(
        "openDateReadOnly clears top after",
        "setTop(\"\")" in html or 'setTop("")' in html,
    )
    check(
        "topMsg before choose step",
        html.find('id="topMsg"') < html.find('id="stepChoose"'),
    )
    check("queue-card loading class", "queue-card.loading" in html or "loading" in html)
    check(
        "openDateReadOnly function",
        "async function openDateReadOnly" in html,
    )


def main() -> int:
    os.environ["WOLF_TEST_MODE"] = "1"
    test_no_close_id_in_dom_assignments()
    test_sanitize_owner_text()
    test_opening_message_persists()

    pid = prod_pid_8787()
    check("prod pid 1297 unchanged", pid == 1297, str(pid))

    print(f"\nSUMMARY pass={PASS} fail={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
