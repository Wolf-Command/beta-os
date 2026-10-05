#!/usr/bin/env python3
"""Beta Owner Trading — READ-ONLY V1 surface loader.

Fail-closed. No live broker. No invented holdings/trades.
staff_ready=false. NOT REBUILT+PROVEN.

Intended mount (Mac apply): beta-os serve route
  GET /api/owner/trading-ro
Prod :8787 must remain untouched.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))

# V1 SoT paths (Mac Studio / wolfterminal)
DEFAULT_TRADING_DESK = Path.home() / ".openclaw/workspace/wolf-system/trading-desk"
DEFAULT_JOURNAL = DEFAULT_TRADING_DESK / "journal.jsonl"
DEFAULT_HOLDINGS_MD = Path.home() / (
    "WolfCommandSystem/WolfCommand/01-Wolf-Command/System-Registry/HOLDINGS-PERSONAL.md"
)
# Optional beta override via env for tests
TRADING_DESK = Path(os.environ.get("BETA_TRADING_DESK", str(DEFAULT_TRADING_DESK)))
JOURNAL_PATH = Path(os.environ.get("BETA_TRADING_JOURNAL", str(DEFAULT_JOURNAL)))
HOLDINGS_PATH = Path(os.environ.get("BETA_HOLDINGS_MD", str(DEFAULT_HOLDINGS_MD)))

EXAMPLE_HOLDINGS_MARKERS = ("Example shape", "- BTC 0", "- ASX:?? 0")


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")


def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok,
        "reason": reason,
        "staff_ready": False,
        "live_broker": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN",
        "migration_state": "PARTIAL",
        "read_only": True,
        "as_of_wita": _now_wita(),
    }
    out.update(extra)
    return out


def _parse_holdings_md(text: str) -> dict[str, Any]:
    """Parse HOLDINGS-PERSONAL.md without inventing a book.

    Template examples (BTC 0 / ASX:?? 0 under 'Example shape') are NOT holdings.
    Empty / template-only → holdings_unknown.
    """
    lines = [ln.rstrip() for ln in text.splitlines()]
    useful: list[str] = []
    in_example = False
    for ln in lines:
        s = ln.strip()
        if "Example shape" in s:
            in_example = True
            continue
        if in_example and (not s or s.startswith("#")):
            in_example = False
        if in_example:
            continue
        if s.startswith("- ") and len(s) > 2:
            # skip pure template leftovers if still present
            if s in ("- BTC 0", "- ASX:?? 0"):
                continue
            useful.append(s[2:].strip())
    if not useful:
        return {
            "holdings_status": "UNKNOWN",
            "holdings_count": 0,
            "holdings": [],
            "note": "HOLDINGS-PERSONAL empty or template-only; do not invent a book",
        }
    return {
        "holdings_status": "PRESENT",
        "holdings_count": len(useful),
        "holdings": useful[:50],  # cap
        "note": "read from HOLDINGS-PERSONAL.md; paper glance only; no broker",
    }


def _read_journal(path: Path, sample_limit: int = 5) -> dict[str, Any]:
    if not path.is_file():
        return {
            "journal_status": "MISSING",
            "journal_rows": 0,
            "journal_sample": [],
            "path": str(path),
            "error": "journal.jsonl not found",
        }
    rows: list[Any] = []
    errors = 0
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    errors += 1
                    rows.append({"_raw_truncated": line[:200]})
    except OSError as e:
        return {
            "journal_status": "ERROR",
            "journal_rows": 0,
            "journal_sample": [],
            "path": str(path),
            "error": str(e),
        }
    sample = rows[-sample_limit:] if rows else []
    return {
        "journal_status": "PRESENT" if rows else "EMPTY",
        "journal_rows": len(rows),
        "journal_sample": sample,
        "parse_errors": errors,
        "path": str(path),
    }


def load_trading_ro() -> dict[str, Any]:
    """Assemble fail-closed trading RO payload from V1 files if present."""
    desk_exists = TRADING_DESK.is_dir()
    provenance = {
        "trading_desk": str(TRADING_DESK),
        "journal": str(JOURNAL_PATH),
        "holdings_md": str(HOLDINGS_PATH),
        "desk_exists": desk_exists,
    }

    holdings_block: dict[str, Any]
    if HOLDINGS_PATH.is_file():
        try:
            holdings_block = _parse_holdings_md(HOLDINGS_PATH.read_text(encoding="utf-8"))
            holdings_block["path"] = str(HOLDINGS_PATH)
        except OSError as e:
            holdings_block = {
                "holdings_status": "ERROR",
                "holdings_count": 0,
                "holdings": [],
                "path": str(HOLDINGS_PATH),
                "error": str(e),
            }
    else:
        holdings_block = {
            "holdings_status": "MISSING",
            "holdings_count": 0,
            "holdings": [],
            "path": str(HOLDINGS_PATH),
            "error": "HOLDINGS-PERSONAL.md not found",
        }

    journal_block = _read_journal(JOURNAL_PATH)

    # Desk docs presence (names only)
    docs_present: list[str] = []
    if desk_exists:
        for name in ("README.md", "QUANT_PROGRAM.md", "PAPER_QUANT_PRACTICE_BRIEF.md"):
            if (TRADING_DESK / name).is_file():
                docs_present.append(name)

    any_sot = (
        holdings_block.get("holdings_status") in ("PRESENT", "UNKNOWN")
        or journal_block.get("journal_status") in ("PRESENT", "EMPTY")
        or bool(docs_present)
    )

    if not any_sot and not desk_exists and holdings_block.get("holdings_status") == "MISSING":
        return _stamp(
            False,
            "NO_SOT_YET",
            surface="owner_trading",
            provenance=provenance,
            holdings=holdings_block,
            journal=journal_block,
            paper_quant_docs=docs_present,
            banner="Paper only. Nothing trades. No live broker. V1 SoT not reachable.",
        )

    return _stamp(
        True,
        "V1_RO_OK" if journal_block.get("journal_status") != "ERROR" else "V1_RO_PARTIAL",
        surface="owner_trading",
        provenance=provenance,
        holdings=holdings_block,
        journal=journal_block,
        paper_quant_docs=docs_present,
        banner="Paper only. Nothing trades. No live broker. Read-only V1 mirror.",
    )


def as_json_bytes(payload: dict[str, Any] | None = None) -> bytes:
    data = payload if payload is not None else load_trading_ro()
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


if __name__ == "__main__":
    print(as_json_bytes().decode("utf-8"))
