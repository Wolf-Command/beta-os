#!/usr/bin/env python3
"""Read-only Model C evidence recon — 2026-09-19.

Proves 77 ledger rows, locked credits, recon note, and WIP four digests.
Does not write the ledger. Does not touch Production.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from core.progress_read_model import (  # noqa: E402
    EXPECTED_CAPABILITY_COUNT,
    SYSTEM_MATURITY_CREDITS,
    compute_system_from_ledger,
)

PASS = 0
FAIL = 0

LEDGER = ROOT / "state" / "model-c-baseline-assessments.json"
HISTORY = ROOT / "state" / "model-c-score-history.jsonl"
NOTE = ROOT / "docs" / "deliveries" / "MODEL-C-EVIDENCE-RECON-2026-09-19.md"
CREDITS_DOC = ROOT / "docs" / "MODEL-C-SYSTEM-NUMERIC-CREDITS.md"
CATALOG = ROOT / "docs" / "MODEL-C-CAPABILITY-CATALOG.md"

LOCKED = {
    "ABSENT": Decimal("0.00"),
    "SPECIFIED": Decimal("0.05"),
    "BUILT": Decimal("0.25"),
    "PROVEN": Decimal("0.80"),
    "READY": Decimal("1.00"),
}
WIP = {
    "scripts/migrations/migrate_phase2_6_team_readiness.py":
        "a8e89d399bd33ec11135b8caaa002a0d18c70000b6a8972d46811d30a61c9881",
    "scripts/phase26_team.py":
        "7c3690afaea97d8fdb48422bf4cbc8e144c9ecfac45c24c19977e83d45088fe0",
    "scripts/skills/__init__.py":
        "edfb69ce6d8f92a88ee6bf6a8160d9926765843271961bba52a3754450c93105",
    "scripts/wolf_intelligence.py":
        "e1de6a248512bcdaf6e71c4db30dc80a229055c7707e682c73d9349acb9bc21b",
}
BACKLOG_ALREADY_TABLED = ("CAP-FIN-05", "CAP-HR-04", "CAP-MSC-05")
SNAPSHOT = {
    "CAP-INTEL-01": "BUILT",
    "CAP-INTEL-02": "PROVEN",
    "CAP-INTEL-03": "PROVEN",
    "CAP-INTEL-04": "PROVEN",
    "CAP-FIN-05": "SPECIFIED",
    "CAP-HR-04": "SPECIFIED",
    "CAP-INTG-07": "SPECIFIED",
    "CAP-MSC-05": "SPECIFIED",
    "CAP-DR-01": "SPECIFIED",
}


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}" + (f" — {detail}" if detail else ""))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_mentions() -> dict[str, set[str]]:
    pat = re.compile(r"CAP-[A-Z]+-\d+")
    found: dict[str, set[str]] = {}
    for path in (ROOT / "scripts").rglob("*.py"):
        rel = str(path.relative_to(ROOT))
        if "test_model_c_evidence_recon.py" in rel or "__pycache__" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for cap_id in pat.findall(text):
            found.setdefault(cap_id, set()).add(rel)
    return found


def honesty_sample(ledger: dict) -> list[str]:
    mentions = code_mentions()
    pool = sorted(
        cap_id
        for cap_id, row in ledger.items()
        if row and row[0] == "SPECIFIED" and cap_id not in mentions
        and cap_id not in BACKLOG_ALREADY_TABLED
    )
    return random.Random(20260919).sample(pool, 5)


def main() -> int:
    check("ledger_exists", LEDGER.is_file())
    check("history_exists", HISTORY.is_file())
    check("recon_note_exists", NOTE.is_file())
    check("credits_doc_exists", CREDITS_DOC.is_file())
    if not LEDGER.is_file() or not NOTE.is_file():
        print(f"\nMODEL-C EVIDENCE RECON: PASS={PASS} FAIL={FAIL}")
        return 1

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    check("ledger_row_count_77", isinstance(ledger, dict) and len(ledger) == 77, str(len(ledger) if isinstance(ledger, dict) else type(ledger)))

    catalog_ids = []
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| (CAP-[A-Z]+-\d+) \|", line)
        if m:
            catalog_ids.append(m.group(1))
    check("catalog_77", len(catalog_ids) == 77, str(len(catalog_ids)))
    check(
        "ledger_matches_catalog",
        set(catalog_ids) == set(ledger),
        str(set(catalog_ids) ^ set(ledger)),
    )

    check(
        "credits_map_locked",
        SYSTEM_MATURITY_CREDITS == LOCKED and EXPECTED_CAPABILITY_COUNT == 77,
        str(SYSTEM_MATURITY_CREDITS),
    )
    credits_text = CREDITS_DOC.read_text(encoding="utf-8")
    for state, credit in (
        ("ABSENT", "0.00"),
        ("SPECIFIED", "0.05"),
        ("BUILT", "0.25"),
        ("PROVEN", "0.80"),
        ("READY", "1.00"),
    ):
        check(
            f"credits_doc_{state}",
            f"| {state} | {credit} |" in credits_text,
        )

    system = compute_system_from_ledger(LEDGER)
    check("system_ok", system.get("ok") is True and system.get("n") == 77, str(system.get("status")))
    note = NOTE.read_text(encoding="utf-8")
    exact = str(system.get("sum_credits_exact"))
    pct = system.get("system_pct")
    check("note_has_sum_credits", exact in note, exact)
    check("note_has_audited_pct", f"{pct}%" in note, str(pct))
    check("note_denominator_77", "/ 77" in note or "/77" in note)
    check("note_no_score_gaming", "No score gaming." in note)
    check("note_ledger_write_none", "Ledger write: none." in note)
    for label in ("KEEP", "UNDER-EVIDENCED", "OVER-CLAIMED", "EVIDENCE-BINDED"):
        check(f"note_has_{label}", label in note)

    tip = json.loads(HISTORY.read_text(encoding="utf-8").strip().splitlines()[-1])
    check("note_has_history_tip_event", tip.get("event") in note, str(tip.get("event")))
    check("note_has_history_tip_sum", str(tip.get("sum_credits")) in note, str(tip.get("sum_credits")))

    for cap_id, state in SNAPSHOT.items():
        got = ledger.get(cap_id, [None])[0]
        check(f"snapshot_{cap_id}", got == state, str(got))

    sample = honesty_sample(ledger)
    check("honesty_sample_len", len(sample) == 5, str(sample))
    for cap_id in sample:
        row_ok = ledger.get(cap_id, [None])[0] == "SPECIFIED"
        line = next((ln for ln in note.splitlines() if cap_id in ln), "")
        check(
            f"honesty_{cap_id}",
            row_ok and "KEEP" in line and "SPECIFIED" in line,
            line or "missing",
        )

    for rel, digest in WIP.items():
        path = ROOT / rel
        got = sha(path) if path.is_file() else ""
        check(f"wip_{path.name}", got == digest, got[:12])

    print(f"\nMODEL-C EVIDENCE RECON: PASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
