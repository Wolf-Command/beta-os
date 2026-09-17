#!/usr/bin/env python3
"""Model C credit-table consistency — active credits must match between canon docs.

Fails if scoring rules still present 0.50 or 0.75 as unmarked active credits.
CLAIMED ≠ VERIFIED.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCORING = ROOT / "docs" / "MODEL-C-SYSTEM-SCORING-RULES.md"
CREDITS = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"

ACTIVE = {
    "ABSENT": "0.00",
    "SPECIFIED": "0.05",
    "BUILT": "0.25",
    "PROVEN": "0.80",
    "READY": "1.00",
}

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


def parse_active_credit_table(text: str) -> dict[str, str]:
    """Parse | STATE | N.NN | rows from the first active credits table.

    Stops at SUPERSEDED / history markers so obsolete rows are ignored.
    """
    found: dict[str, str] = {}
    in_superseded = False
    for line in text.splitlines():
        upper = line.upper()
        if "SUPERSEDED" in upper or "HISTORY ONLY" in upper or "DO NOT USE" in upper:
            # Once we enter a superseded block, skip until a new active table header
            if "|" not in line or "STATE" in upper:
                in_superseded = True
            continue
        if in_superseded:
            if line.strip().startswith("| State") or line.strip().startswith("| STATE"):
                in_superseded = False
            else:
                continue
        m = re.match(
            r"\|\s*\*?\*?([A-Z]+)\*?\*?\s*\|\s*([0-9]+\.[0-9]+)\s*\|",
            line.strip(),
        )
        if m and m.group(1) in ACTIVE:
            found[m.group(1)] = m.group(2)
    return found


def active_body_without_superseded(text: str) -> str:
    """Strip SUPERSEDED / history-only blocks (blockquote or labeled paragraphs)."""
    lines = []
    skip = False
    for line in text.splitlines():
        upper = line.upper()
        if "SUPERSEDED" in upper or "HISTORY ONLY" in upper:
            skip = True
            continue
        if skip:
            # End skip at blank line after a superseded note, or next ## heading
            if line.startswith("##") or (line.strip() == "" and lines and lines[-1].strip() == ""):
                skip = False
            elif line.startswith(">"):
                continue
            elif "0.50" in line or "0.75" in line:
                continue
            else:
                skip = False
        if not skip:
            lines.append(line)
    return "\n".join(lines)


def main() -> int:
    check("scoring_rules_exists", SCORING.is_file())
    check("numeric_credits_exists", CREDITS.is_file())
    if not SCORING.is_file() or not CREDITS.is_file():
        print(f"\nMODEL-C CREDIT CONSISTENCY: PASS={PASS} FAIL={FAIL}")
        return 1

    scoring_text = SCORING.read_text(encoding="utf-8")
    credits_text = CREDITS.read_text(encoding="utf-8")

    scoring_table = parse_active_credit_table(scoring_text)
    credits_table = parse_active_credit_table(credits_text)

    check(
        "numeric_credits_has_full_active_table",
        credits_table == ACTIVE,
        str(credits_table),
    )
    check(
        "scoring_rules_has_full_active_table",
        scoring_table == ACTIVE,
        str(scoring_table),
    )
    check(
        "active_tables_agree",
        scoring_table == credits_table == ACTIVE,
        f"scoring={scoring_table} credits={credits_table}",
    )

    # Active (non-superseded) body must not present 0.50 / 0.75 as credits
    active_scoring = active_body_without_superseded(scoring_text)
    # Also drop the explicit SUPERSEDED blockquote if still present via line starts
    unmarked_050 = bool(re.search(r"(?<![0-9])0\.50(?![0-9])", active_scoring))
    unmarked_075 = bool(re.search(r"(?<![0-9])0\.75(?![0-9])", active_scoring))
    # Allow mention only inside SUPERSEDED-labeled context — already stripped
    check("scoring_no_active_0.50", not unmarked_050)
    check("scoring_no_active_0.75", not unmarked_075)

    # Inline prose credit list in §2 must not use obsolete numbers as current
    obsolete_inline = re.search(
        r"SPECIFIED\s+0\.25\s*[·•]\s*BUILT\s+0\.50\s*[·•]\s*PROVEN\s+0\.75",
        active_scoring,
        re.IGNORECASE,
    )
    check("scoring_no_obsolete_inline_credit_list", obsolete_inline is None)

    # v1.0 active inline must be present somewhere
    has_v1 = (
        "0.05" in scoring_text
        and "0.80" in scoring_text
        and "SPECIFIED" in scoring_text
        and "PROVEN" in scoring_text
    )
    check("scoring_states_v1_credits", has_v1)

    print(f"\nMODEL-C CREDIT CONSISTENCY: PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
