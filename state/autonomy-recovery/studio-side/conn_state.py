#!/usr/bin/env python3
"""Parse WorkspaceConnectionService lines from renderer/main logs.

States: connected | reconnecting | disconnected | failed | unknown
PIPE_DEAD when latest bad state has age >= DEAD_AFTER_SEC (default 180).

Historical note (2026-10-05/06): the only WCS line in session 20261004T184453
is the 06:43:35 promotion with priorState=reconnecting. Parser treats priorState
as the implied state for all as_of < promotion_ts (REPLAY inference, not a
fabricated log line).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

LOG_TS = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)"
)
WCS = re.compile(r"\[WorkspaceConnectionService\]\s*(?P<msg>.*)$")
PRIOR = re.compile(r'"priorState"\s*:\s*"(?P<p>[^"]+)"')
DEAD_AFTER_SEC = 180
BAD = frozenset({"reconnecting", "disconnected", "failed", "offline"})
GOOD = frozenset({"connected", "online"})


@dataclass
class ConnEvent:
    ts: datetime
    state: str
    raw: str
    implied: bool = False  # True if derived from priorState, not an explicit line


def _parse_ts(s: str) -> datetime:
    # local naive WITA wall clock as written in logs
    if "." in s:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def parse_line(line: str) -> list[ConnEvent]:
    """Return 0..2 events for a single log line."""
    m = LOG_TS.match(line.strip())
    if not m or "WorkspaceConnectionService" not in line:
        return []
    ts = _parse_ts(m.group("ts"))
    w = WCS.search(line)
    msg = (w.group("msg") if w else line).lower()
    out: list[ConnEvent] = []
    prior_m = PRIOR.search(line)
    prior = prior_m.group("p").lower() if prior_m else None

    if "promoted workspace to connected" in msg or (
        "connected" in msg and "promoted" in msg
    ):
        if prior and prior in BAD:
            # implied state before this promotion
            out.append(ConnEvent(ts=ts, state=prior, raw=line.strip(), implied=True))
        out.append(ConnEvent(ts=ts, state="connected", raw=line.strip(), implied=False))
        return out
    if "resolution failed" in msg or "without regaining connection" in msg:
        out.append(ConnEvent(ts=ts, state="failed", raw=line.strip()))
        return out
    if "reconnecting" in msg or (prior == "reconnecting"):
        out.append(ConnEvent(ts=ts, state="reconnecting", raw=line.strip()))
        return out
    if "disconnect" in msg:
        out.append(ConnEvent(ts=ts, state="disconnected", raw=line.strip()))
        return out
    return out


def parse_text(text: str) -> list[ConnEvent]:
    ev: list[ConnEvent] = []
    for line in text.splitlines():
        ev.extend(parse_line(line))
    ev.sort(key=lambda e: (e.ts, 0 if e.implied else 1))
    return ev


def state_as_of(events: list[ConnEvent], as_of: datetime) -> tuple[str, Optional[datetime]]:
    """Return (state, since_ts) valid at as_of.

    Implied priorState events apply strictly before their timestamp.
    Explicit events apply at and after their timestamp.
    """
    applicable: list[ConnEvent] = []
    for e in events:
        if e.implied:
            if as_of < e.ts:
                applicable.append(e)
        else:
            if as_of >= e.ts:
                applicable.append(e)
    if not applicable:
        return "unknown", None
    # latest by ts then explicit over implied
    applicable.sort(key=lambda e: (e.ts, 0 if e.implied else 1))
    last = applicable[-1]
    # since: for implied reconnecting before promotion, since is unknown → use as_of window start caller-side
    return last.state, last.ts


def pipe_from_conn(state: str, age_s: Optional[float], dead_after: float = DEAD_AFTER_SEC) -> tuple[bool, str]:
    if state in GOOD:
        return True, "CONN_CONNECTED"
    if state in BAD:
        if age_s is None:
            return False, f"CONN_{state.upper()}_AGE_UNKNOWN"
        if age_s >= dead_after:
            return False, f"CONN_{state.upper()}_AGE_{int(age_s)}"
        return True, f"CONN_{state.upper()}_GRACE_{int(age_s)}"
    return True, "CONN_UNKNOWN_NO_VOTE"  # don't flip PIPE on unknown alone


def tail_text(path: Path, max_bytes: int = 256_000) -> str:
    with path.open("rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - max_bytes))
        return f.read().decode("utf-8", errors="replace")


def find_renderer_logs(root: Optional[Path] = None) -> list[Path]:
    root = root or (Path.home() / "Library/Application Support/Cursor/logs")
    if not root.exists():
        return []
    files = list(root.glob("*/window*/renderer.log"))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def scan_live(dead_after: float = DEAD_AFTER_SEC, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now()
    files = find_renderer_logs()
    events: list[ConnEvent] = []
    used: list[str] = []
    for p in files[:12]:  # newest sessions only
        try:
            text = tail_text(p)
        except Exception:
            continue
        ev = parse_text(text)
        if ev:
            events.extend(ev)
            used.append(str(p))
    events.sort(key=lambda e: (e.ts, 0 if e.implied else 1))
    state, since = state_as_of(events, now)
    age = (now - since).total_seconds() if since and not (
        # if only implied event in future relative... handled by state_as_of
        False
    ) else None
    # For implied-only applicability (as_of < promotion): since is promotion ts of implied event
    # Age of reconnecting before promotion: use now-as_of in replay; live: if state bad and since is promotion time while implied, age is large
    if state in BAD and since is not None:
        # If latest applicable is implied, 'since' is the promotion timestamp which is in the future relative to as_of — shouldn't happen for live now>=all
        age = max(0.0, (now - since).total_seconds())
        # If implied reconnecting was recorded AT the promotion ts, for live `now` after promotion we use explicit connected instead
    ok, reason = pipe_from_conn(state, age, dead_after)
    return {
        "conn_state": state,
        "conn_state_age_s": None if age is None else round(age, 1),
        "conn_pipe_ok": ok,
        "conn_reason": reason,
        "conn_log_files": [Path(u).name for u in used[:5]],
        "conn_events": len(events),
    }


def replay_as_of(text: str, as_of: datetime, reconnecting_since: Optional[datetime] = None) -> dict:
    """Replay parser against a log blob at a virtual as_of time.

    If the log only contains a promotion with priorState=reconnecting, then for
    as_of < promotion_ts the state is reconnecting. Pass reconnecting_since
    (e.g. incident 22:55) so age crosses DEAD_AFTER_SEC by ~22:58.
    """
    events = parse_text(text)
    state, since = state_as_of(events, as_of)
    age: Optional[float] = None
    if state in BAD:
        start = reconnecting_since or since
        age = (as_of - start).total_seconds() if start else None
    elif state in GOOD:
        age = (as_of - since).total_seconds() if since else 0.0
    else:
        # No applicable event: if a later connected event implies prior reconnecting
        # and reconnecting_since <= as_of < that promotion, treat as reconnecting.
        for e in events:
            if e.implied and e.state in BAD and as_of < e.ts and (
                reconnecting_since is None or as_of >= reconnecting_since
            ):
                state = e.state
                start = reconnecting_since or as_of
                age = (as_of - start).total_seconds()
                break
    ok, reason = pipe_from_conn(state, age)
    return {
        "as_of": as_of.isoformat(sep=" "),
        "conn_state": state,
        "conn_state_age_s": None if age is None else round(age, 1),
        "conn_pipe_ok": ok,
        "conn_reason": reason,
        "pipe": "PIPE_OK" if ok else "PIPE_DEAD",
    }



if __name__ == "__main__":
    import json
    print(json.dumps(scan_live(), indent=2))
