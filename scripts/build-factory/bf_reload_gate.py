#!/usr/bin/env python3
"""Read-only Beta reload gate (Owner order 5 Oct 2026 19:01 WITA; extended by Owner P0 20:00 WITA).

Exit 0 = reload allowed. Exit 3 = RELOAD_HELD (print reasons as JSON).
Held when ANY of:
  * :8788 does not have exactly one listener, or it does not answer /api/health 200;
  * an announced human-test window is open (state/build-factory/HUMAN-TEST-WINDOW.json
    {"until": "<ISO UTC>", "reason": "..."});
  * a Beta reload happened less than COOLDOWN_MIN minutes ago (BETA-RELOAD-LAST.json);
  * Uma Blu close, petty, or Finance activity in core_audit_events in the last 10 min
    (sqlite mode=ro);
  * close / petty / Finance requests by a real session (non-401/403) appear in the Beta
    request log during the observation window.
The gate never reloads anything itself; scripts/beta_restart.py is the only caller that
acts on it. Never touches Production :8787. Never prints process command lines.
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os")
BF = ROOT / "state" / "build-factory"
CATALOG = ROOT / "catalog" / "content_library.sqlite"
BETA_LOG = Path("/tmp/serve_beta.log")
WINDOW_FILE = BF / "HUMAN-TEST-WINDOW.json"
STAMP = BF / "BETA-RELOAD-LAST.json"
WINDOW_MIN = 10
COOLDOWN_MIN = 15
OBSERVE_SECS = 45
CLOSE_RE = re.compile(r"uma-blu-close|venue[-_]close|daily[-_]close|/petty|petty[-_]", re.I)
FINANCE_RE = re.compile(r"/(bzg|amg|ggv)[-/]finance|/api/(bzg|amg|ggv)/finance|/api/finance|finance-ops|/bzg/finance", re.I)
DENIED_RE = re.compile(r'" (401|403) ')


def _parse_iso(s: str) -> datetime | None:
    try:
        return datetime.strptime(s.replace("+00:00", "Z"), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def _listeners(port: int) -> list[int]:
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], text=True, stderr=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, OSError):
        return []
    return sorted({int(x) for x in out.split() if x.strip().isdigit()})


def _healthy() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8788/api/health", timeout=3) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def _recent_activity_audit() -> dict:
    since = (datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MIN)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = sqlite3.connect(f"file:{CATALOG}?mode=ro", uri=True, timeout=30)
    try:
        close_petty = conn.execute(
            """SELECT COUNT(*) FROM core_audit_events
               WHERE occurred_at >= ?
                 AND (lower(action) LIKE 'venue_close%' OR lower(action) LIKE '%petty%'
                      OR lower(resource_type) LIKE '%close%' OR lower(resource_type) LIKE '%petty%')""",
            (since,),
        ).fetchone()[0]
        finance = conn.execute(
            """SELECT COUNT(*) FROM core_audit_events
               WHERE occurred_at >= ?
                 AND (lower(action) LIKE 'finance%' OR lower(action) LIKE '%.finance%'
                      OR lower(action) LIKE 'bzg.p2p%' OR lower(action) LIKE '%bill%'
                      OR lower(action) LIKE '%nota%' OR lower(action) LIKE '%receive%'
                      OR lower(action) LIKE '%journal%' OR lower(action) LIKE '%recon%'
                      OR lower(resource_type) LIKE '%finance%' OR lower(resource_type) LIKE '%bank%'
                      OR lower(resource_type) LIKE '%bill%' OR lower(resource_type) LIKE '%journal%')""",
            (since,),
        ).fetchone()[0]
        return {"close_petty": int(close_petty or 0), "finance": int(finance or 0)}
    finally:
        conn.close()


def _observe_log(secs: int) -> dict:
    res = {"close_petty": 0, "finance": 0}
    if not BETA_LOG.exists():
        return res
    start = BETA_LOG.stat().st_size
    time.sleep(secs)
    try:
        with BETA_LOG.open("rb") as fh:
            fh.seek(start)
            new = fh.read().decode("utf-8", "replace")
    except OSError:
        return res
    for ln in new.splitlines():
        if DENIED_RE.search(ln):
            continue  # unauthenticated probes are not human activity
        if CLOSE_RE.search(ln):
            res["close_petty"] += 1
        elif FINANCE_RE.search(ln):
            res["finance"] += 1
    return res


def evaluate(observe: int) -> dict:
    reasons: list[str] = []
    now = datetime.now(timezone.utc)
    beta = _listeners(8788)
    prod = _listeners(8787)
    if len(beta) != 1:
        reasons.append(f"beta_listeners={len(beta)}")
    elif not _healthy():
        reasons.append("beta_health_not_200")
    try:
        win = json.loads(WINDOW_FILE.read_text()) if WINDOW_FILE.exists() else None
    except (OSError, ValueError):
        win = None
    if win:
        until = _parse_iso(str(win.get("until", "")))
        if until and until > now:
            reasons.append(f"human_test_window_until={win.get('until')}")
    try:
        st = json.loads(STAMP.read_text()) if STAMP.exists() else None
    except (OSError, ValueError):
        st = None
    if st:
        last = _parse_iso(str(st.get("at", "")))
        if last and now - last < timedelta(minutes=COOLDOWN_MIN):
            reasons.append(f"cooldown_last_reload={st.get('at')}")
    try:
        aud = _recent_activity_audit()
    except sqlite3.Error as exc:
        aud = {"close_petty": -1, "finance": -1}
        reasons.append(f"audit_read_error={exc.__class__.__name__}")
    if aud["close_petty"] > 0:
        reasons.append(f"close_or_petty_audit_last_{WINDOW_MIN}min={aud['close_petty']}")
    if aud["finance"] > 0:
        reasons.append(f"finance_audit_last_{WINDOW_MIN}min={aud['finance']}")
    obs = _observe_log(observe) if not reasons else {"close_petty": 0, "finance": 0, "skipped": True}
    if obs["close_petty"] > 0:
        reasons.append(f"close_or_petty_requests_in_{observe}s={obs['close_petty']}")
    if obs["finance"] > 0:
        reasons.append(f"finance_requests_in_{observe}s={obs['finance']}")
    return {
        "reload_allowed": not reasons,
        "reasons": reasons,
        "beta_listener_pids": beta,
        "prod_listener_pids": prod,
        "prod_1297_listening": 1297 in prod,
        "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main() -> int:
    observe = 5 if "--quick" in sys.argv else OBSERVE_SECS
    out = evaluate(observe)
    print(json.dumps(out))
    return 0 if out["reload_allowed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
