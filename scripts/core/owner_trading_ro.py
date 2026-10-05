#!/usr/bin/env python3
"""Beta Owner Trading — READ-ONLY V1 surface loader (deepened).

Fail-closed. No live broker. No invented holdings/trades.
staff_ready=false. NOT REBUILT+PROVEN.

Mounts (Beta :8788 only):
  GET /api/owner/trading-ro
  GET /api/owner/trading-ro/history  (?limit=1..100)
Prod :8787 must remain untouched.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))

DEFAULT_TRADING_DESK = Path.home() / ".openclaw/workspace/wolf-system/trading-desk"
DEFAULT_JOURNAL = DEFAULT_TRADING_DESK / "journal.jsonl"
DEFAULT_HOLDINGS_MD = Path.home() / (
    "WolfCommandSystem/WolfCommand/01-Wolf-Command/System-Registry/HOLDINGS-PERSONAL.md"
)
TRADING_DESK = Path(os.environ.get("BETA_TRADING_DESK", str(DEFAULT_TRADING_DESK)))
JOURNAL_PATH = Path(os.environ.get("BETA_TRADING_JOURNAL", str(DEFAULT_JOURNAL)))
HOLDINGS_PATH = Path(os.environ.get("BETA_HOLDINGS_MD", str(DEFAULT_HOLDINGS_MD)))

JOURNAL_SAMPLE_DEFAULT = 8
JOURNAL_HISTORY_CAP = 100
EXCERPT_MAX_CHARS = 2200


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
        "honesty": "PARTIAL · paper only · no broker · fail-closed",
    }
    out.update(extra)
    return out


def _parse_holdings_md(text: str) -> dict[str, Any]:
    """Parse HOLDINGS-PERSONAL.md without inventing a book."""
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
        "holdings": useful[:50],
        "note": "read from HOLDINGS-PERSONAL.md; paper glance only; no broker",
    }


def _public_journal_row(row: Any) -> Any:
    """Keep journal fields; drop nothing critical — journal is Owner trade log (not HR PII).
    Cap long free-text notes.
    """
    if not isinstance(row, dict):
        return {"_raw_truncated": str(row)[:200]}
    out: dict[str, Any] = {}
    keep = (
        "id", "act", "source", "created_at", "created_by", "when", "ticker", "side",
        "venue", "live", "status", "margin_mode", "leverage", "size", "entry",
        "planned_entry", "fill", "est_liquidation", "break_even", "margin", "fee",
        "realized_pnl", "unrealized_pnl", "unrealized_pct", "mark", "timeframe",
        "tp_sl", "screenshot_time", "thesis", "planned_stop", "planned_target",
        "notes", "tags", "attachment", "at", "who",
    )
    for k in keep:
        if k in row:
            v = row[k]
            if k in ("notes", "thesis") and isinstance(v, str) and len(v) > 400:
                v = v[:400] + "…"
            out[k] = v
    if not out and "_raw_truncated" in row:
        out["_raw_truncated"] = row["_raw_truncated"]
    return out


def _read_journal(path: Path, sample_limit: int = JOURNAL_SAMPLE_DEFAULT,
                  history_limit: int | None = None) -> dict[str, Any]:
    if not path.is_file():
        return {
            "journal_status": "MISSING",
            "journal_rows": 0,
            "journal_sample": [],
            "journal_history": [],
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
                    rows.append(_public_journal_row(json.loads(line)))
                except json.JSONDecodeError:
                    errors += 1
                    rows.append({"_raw_truncated": line[:200]})
    except OSError as e:
        return {
            "journal_status": "ERROR",
            "journal_rows": 0,
            "journal_sample": [],
            "journal_history": [],
            "path": str(path),
            "error": str(e),
        }
    sample = rows[-sample_limit:] if rows else []
    hist_n = JOURNAL_HISTORY_CAP if history_limit is None else max(0, min(int(history_limit), JOURNAL_HISTORY_CAP))
    history = rows[-hist_n:] if rows else []
    return {
        "journal_status": "PRESENT" if rows else "EMPTY",
        "journal_rows": len(rows),
        "journal_sample": sample,
        "journal_history": history,
        "journal_history_capped_at": hist_n,
        "parse_errors": errors,
        "path": str(path),
    }


def _excerpt_md(path: Path, max_chars: int = EXCERPT_MAX_CHARS) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "MISSING", "path": str(path), "excerpt": "", "chars": 0}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return {"status": "ERROR", "path": str(path), "excerpt": "", "chars": 0, "error": str(e)}
    # Prefer first meaningful section; never invent content
    clipped = text[:max_chars]
    if len(text) > max_chars:
        clipped = clipped.rstrip() + "\n… [truncated — V1 SoT file remains authoritative]"
    return {
        "status": "PRESENT",
        "path": str(path),
        "excerpt": clipped,
        "chars": len(text),
        "truncated": len(text) > max_chars,
    }


def _paper_quant_brief() -> dict[str, Any]:
    quant = TRADING_DESK / "QUANT_PROGRAM.md"
    paper = TRADING_DESK / "PAPER_QUANT_PRACTICE_BRIEF.md"
    readme = TRADING_DESK / "README.md"
    docs_present = [n for n in ("README.md", "QUANT_PROGRAM.md", "PAPER_QUANT_PRACTICE_BRIEF.md")
                    if (TRADING_DESK / n).is_file()]
    return {
        "lock": "Paper only. No broker. No invented prices/levels. Nothing trades until Matthew says.",
        "docs_present": docs_present,
        "quant_program": _excerpt_md(quant),
        "paper_practice": _excerpt_md(paper),
        "readme": _excerpt_md(readme, 800) if readme.is_file() else {"status": "MISSING"},
    }


def load_trading_ro(journal_history_limit: int | None = None) -> dict[str, Any]:
    """Assemble fail-closed trading RO payload from V1 files if present."""
    desk_exists = TRADING_DESK.is_dir()
    provenance = {
        "trading_desk": str(TRADING_DESK),
        "journal": str(JOURNAL_PATH),
        "holdings_md": str(HOLDINGS_PATH),
        "desk_exists": desk_exists,
    }

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

    journal_block = _read_journal(JOURNAL_PATH, history_limit=journal_history_limit)
    paper = _paper_quant_brief()
    docs_present = paper.get("docs_present") or []

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
            paper_quant=paper,
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
        paper_quant=paper,
        paper_quant_docs=docs_present,
        banner="Paper only. Nothing trades. No live broker. Read-only V1 mirror.",
        ui_hints={
            "sections": ["honesty", "holdings", "journal", "paper_quant"],
            "mutations": False,
            "broker": False,
        },
    )


def load_trading_history(limit: int = 50) -> dict[str, Any]:
    """History-focused payload (same SoT, larger journal window)."""
    lim = max(1, min(int(limit), JOURNAL_HISTORY_CAP))
    base = load_trading_ro(journal_history_limit=lim)
    base["endpoint"] = "trading-ro/history"
    base["requested_limit"] = lim
    return base


def as_json_bytes(payload: dict[str, Any] | None = None) -> bytes:
    data = payload if payload is not None else load_trading_ro()
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


if __name__ == "__main__":
    print(as_json_bytes().decode("utf-8"))
