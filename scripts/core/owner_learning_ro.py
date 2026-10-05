#!/usr/bin/env python3
"""Beta Owner Learning Desk — READ-ONLY V1 state loader.

TTC paper only. Nothing trades. Fail-closed.
No live quant exec. Distinct from /intel/learning.
staff_ready=false. NOT REBUILT+PROVEN.

Mount: GET /api/owner/learning-ro
Prod :8787 untouched.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

WITA = timezone(timedelta(hours=8))

DEFAULT_STATE = Path.home() / ".openclaw/workspace/wolf-system/state/learning-desk"
STATE_DIR = Path(os.environ.get("BETA_LEARNING_STATE", str(DEFAULT_STATE)))
TRACKS_PATH = Path(os.environ.get("BETA_LEARNING_TRACKS", str(STATE_DIR / "tracks.json")))
INBOX_PATH = Path(os.environ.get("BETA_LEARNING_INBOX", str(STATE_DIR / "inbox.jsonl")))
DEFAULT_TRADING_DESK = Path.home() / ".openclaw/workspace/wolf-system/trading-desk"
TRADING_DESK = Path(os.environ.get("BETA_TRADING_DESK", str(DEFAULT_TRADING_DESK)))

RECENT_ITEM_CAP = 40


def _now_wita() -> str:
    return datetime.now(WITA).strftime("%Y-%m-%dT%H:%M:%S%z")


def _stamp(ok: bool, reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "ok": ok,
        "reason": reason,
        "staff_ready": False,
        "live_quant": False,
        "claim": "NOT_REBUILT_PLUS_PROVEN",
        "migration_state": "PARTIAL",
        "read_only": True,
        "as_of_wita": _now_wita(),
        "honesty": "PARTIAL · TTC paper only · nothing trades · ≠ /intel/learning",
        "distinct_from": "/intel/learning",
    }
    out.update(extra)
    return out


def _public_item(row: dict[str, Any]) -> dict[str, Any]:
    """Titles/status/track only — no transcript body / preview dump."""
    return {
        "id": row.get("id"),
        "title": row.get("title") or row.get("filename") or row.get("id"),
        "status": row.get("status"),
        "track": row.get("track"),
        "kind": row.get("kind"),
        "source": row.get("source"),
        "added_at": row.get("added_at"),
        "research_status": row.get("research_status"),
    }


def _load_tracks() -> dict[str, Any]:
    if not TRACKS_PATH.is_file():
        return {"status": "MISSING", "path": str(TRACKS_PATH), "tracks": []}
    try:
        raw = json.loads(TRACKS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {"status": "ERROR", "path": str(TRACKS_PATH), "tracks": [], "error": str(e)}
    tracks_out = []
    for tid, t in (raw.get("tracks") or {}).items():
        if not isinstance(t, dict):
            continue
        ids = t.get("item_ids") or []
        tracks_out.append({
            "id": t.get("id") or tid,
            "status": t.get("status"),
            "started_at": t.get("started_at"),
            "item_count": len(ids) if isinstance(ids, list) else 0,
            # do not dump full item_ids list if huge — cap
            "item_ids_sample": (ids[:12] if isinstance(ids, list) else []),
        })
    return {
        "status": "PRESENT",
        "path": str(TRACKS_PATH),
        "tracks": tracks_out,
        "track_count": len(tracks_out),
    }


def _load_inbox(limit: int = RECENT_ITEM_CAP) -> dict[str, Any]:
    if not INBOX_PATH.is_file():
        return {
            "status": "MISSING",
            "path": str(INBOX_PATH),
            "counts": {"all": 0},
            "recent": [],
        }
    rows: list[dict[str, Any]] = []
    errors = 0
    try:
        with INBOX_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    errors += 1
    except OSError as e:
        return {
            "status": "ERROR",
            "path": str(INBOX_PATH),
            "counts": {"all": 0},
            "recent": [],
            "error": str(e),
        }
    by_status: dict[str, int] = {}
    by_track: dict[str, int] = {}
    for r in rows:
        st = str(r.get("status") or "unknown")
        by_status[st] = by_status.get(st, 0) + 1
        tr = str(r.get("track") or "(none)")
        by_track[tr] = by_track.get(tr, 0) + 1
    recent = [_public_item(r) for r in rows[-limit:]]
    recent.reverse()  # newest first if file is append-order
    return {
        "status": "PRESENT",
        "path": str(INBOX_PATH),
        "counts": {
            "all": len(rows),
            "by_status": by_status,
            "by_track": by_track,
        },
        "recent": recent,
        "parse_errors": errors,
    }


def load_learning_ro() -> dict[str, Any]:
    provenance = {
        "state_dir": str(STATE_DIR),
        "tracks": str(TRACKS_PATH),
        "inbox": str(INBOX_PATH),
        "state_exists": STATE_DIR.is_dir(),
    }
    tracks = _load_tracks()
    inbox = _load_inbox()
    paper_docs = []
    if TRADING_DESK.is_dir():
        for name in ("QUANT_PROGRAM.md", "PAPER_QUANT_PRACTICE_BRIEF.md"):
            if (TRADING_DESK / name).is_file():
                paper_docs.append(name)
    ttc_base = STATE_DIR / "ttc-learn-base"
    ttc_meta = {
        "path": str(ttc_base),
        "exists": ttc_base.is_dir(),
        "entry_count_hint": None,
    }
    entries = ttc_base / "entries.jsonl"
    if entries.is_file():
        try:
            with entries.open("r", encoding="utf-8") as f:
                ttc_meta["entry_count_hint"] = sum(1 for ln in f if ln.strip())
        except OSError:
            pass

    any_sot = (
        tracks.get("status") == "PRESENT"
        or inbox.get("status") == "PRESENT"
        or provenance["state_exists"]
    )
    if not any_sot:
        return _stamp(
            False,
            "NO_SOT_YET",
            surface="owner_learning",
            provenance=provenance,
            tracks=tracks,
            inbox=inbox,
            paper_quant_docs=paper_docs,
            ttc_learn_base=ttc_meta,
            banner="V1 learning-desk state not found. TTC paper only. Nothing trades.",
        )

    return _stamp(
        True,
        "V1_RO_OK",
        surface="owner_learning",
        provenance=provenance,
        tracks=tracks,
        inbox=inbox,
        paper_quant_docs=paper_docs,
        ttc_learn_base=ttc_meta,
        banner="Owner Learning · V1 state read-only · TTC paper only · nothing trades · ≠ Intel Learning Policy",
        ui_hints={
            "sections": ["honesty", "tracks", "recent_items", "paper_quant_docs"],
            "mutations": False,
            "live_quant": False,
        },
    )


def as_json_bytes(payload: dict[str, Any] | None = None) -> bytes:
    data = payload if payload is not None else load_learning_ro()
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")


if __name__ == "__main__":
    print(as_json_bytes().decode("utf-8"))
