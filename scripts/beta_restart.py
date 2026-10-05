#!/usr/bin/env python3
"""Single, graceful, gated Beta (:8788) reload — the ONLY sanctioned restart path.

Owner P0 5 Oct 2026 20:00 WITA (incident: restart loop 19:54-20:00, Cloudflare 502
on beta.wolfcommand.net). Root cause: regression test files called this script
unconditionally from their own main(); every test re-run kickstarted Beta, and
launchd's respawn throttle (5-10 s) left :8788 with no listener -> 502.

Rules enforced here (callers cannot bypass them):
  * launchd (net.wolfcommand.serve-beta, KeepAlive) is the single owner of Beta
    processes. This script only asks launchd for ONE `kickstart -k`; it never
    retries a kickstart, never starts serve_beta itself, never kills a pid.
  * Every reload must pass scripts/build-factory/bf_reload_gate.py (Uma close,
    petty, Finance activity, announced human-test window, cooldown, listener count).
  * Cooldown: at most one reload per COOLDOWN_MIN minutes (stamp file).
  * Reloads requested from inside a test run (unittest/pytest, or
    BF_IN_TEST=1) are refused: tests are in-process and must never restart Beta.
  * Graceful: after the kickstart, the new listener must answer GET /api/health 200
    on 3 consecutive probes before the reload is reported UP.
  * A cross-process flock stops two reloads racing.

Exit codes: 0 reloaded and healthy; 3 RELOAD_HELD (not an error for callers);
1 reload attempted but new listener not healthy in time (launchd KeepAlive still
owns recovery — we do NOT kick again); 2 refused (production lane / misuse).
Never touches Production :8787. Never prints process command lines.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LABEL = "net.wolfcommand.serve-beta"
BETA_PORT = 8788
PROD_PORT = 8787
ROOT = Path("/Users/wolfterminal/beta-os")
BF = ROOT / "state" / "build-factory"
STAMP = BF / "BETA-RELOAD-LAST.json"
LOG = BF / "BETA-RELOAD-LOG.jsonl"
FLOCK = BF / "BETA-RELOAD.flock"
GATE = ROOT / "scripts" / "build-factory" / "bf_reload_gate.py"
COOLDOWN_MIN = 15
HEALTH_URL = f"http://127.0.0.1:{BETA_PORT}/api/health"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def listeners(port: int) -> list[int]:
    try:
        out = subprocess.check_output(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                                      text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, OSError):
        return []
    return sorted({int(x) for x in out.split() if x.strip().isdigit()})


def healthy() -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=3) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def log_event(ev: dict) -> None:
    ev.setdefault("at", now_iso())
    ev.setdefault("caller_ppid", os.getppid())
    ev.setdefault("caller", os.environ.get("BF_RELOAD_CALLER", ""))
    try:
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev) + "\n")
    except OSError:
        pass


def in_test_context() -> bool:
    if os.environ.get("BF_IN_TEST") == "1" or os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    # Parent process is a test file (scripts/tests/test_*.py or migrations) -> refuse.
    caller = os.environ.get("BF_RELOAD_CALLER", "")
    if caller.startswith("test_"):
        return True
    try:
        main_mod = sys.modules.get("__main__")
        if main_mod and Path(getattr(main_mod, "__file__", "") or "").name.startswith("test_"):
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def parent_is_test() -> bool:
    """Detect the classic offender: a test/migration script that subprocess-runs us.

    Walks up to 4 ancestors and inspects their argv internally (never printed/logged).
    """
    try:
        pid = os.getppid()
        for _ in range(4):
            if pid <= 1:
                break
            comm = subprocess.check_output(["ps", "-o", "comm=", "-p", str(pid)], text=True,
                                           stderr=subprocess.DEVNULL).strip().lower()
            args = ""
            if "python" in comm:  # only python ancestors (a shell's -c string is not a test run)
                args = subprocess.check_output(["ps", "-o", "args=", "-p", str(pid)], text=True,
                                               stderr=subprocess.DEVNULL)
            if args and re.search(r"(scripts/tests/test_|/tests/test_|migrations/migrate_|\btest_[A-Za-z0-9_]+\.py|pytest|unittest)", args):
                return True
            ppid = subprocess.check_output(["ps", "-o", "ppid=", "-p", str(pid)], text=True,
                                           stderr=subprocess.DEVNULL).strip()
            pid = int(ppid or 0)
    except Exception:  # noqa: BLE001
        return False
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Gated, graceful Beta reload via launchd only")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wait-secs", type=float, default=45.0)
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    if in_test_context() or parent_is_test():
        msg = {"result": "RELOAD_HELD", "reasons": ["called_from_test_or_migration: tests are in-process and must never restart Beta"]}
        print(json.dumps(msg))
        log_event({"event": "RELOAD_REFUSED_TEST_CALLER", **msg})
        return 3

    BF.mkdir(parents=True, exist_ok=True)
    with FLOCK.open("w") as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            msg = {"result": "RELOAD_HELD", "reasons": ["another_reload_in_progress"]}
            print(json.dumps(msg)); log_event({"event": "RELOAD_HELD", **msg})
            return 3

        gate = subprocess.run([sys.executable, str(GATE)], capture_output=True, text=True)
        try:
            gate_json = json.loads(gate.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            gate_json = {"raw": gate.stdout[-400:]}
        if gate.returncode != 0:
            msg = {"result": "RELOAD_HELD", "reasons": gate_json.get("reasons", ["gate_failed"]), "gate": gate_json}
            print(json.dumps(msg)); log_event({"event": "RELOAD_HELD", **msg})
            return 3

        before = listeners(BETA_PORT)
        if args.dry_run:
            print(json.dumps({"result": "DRY_RUN_ALLOWED", "gate": gate_json, "before": before}))
            return 0

        # Owner P0 5 Oct 2026 20:30 WITA: COMMIT + PUSH the live Beta tree to GitHub
        # (wolfcommand/beta-os, branch beta) BEFORE reloading, so a reviewable diff exists.
        # Non-fatal: a push failure is recorded (GIT-SNAPSHOT-LAST.json) and blocks HUMAN READY
        # for P0 slices, but never blocks or breaks the reload itself. See docs/BETA-GITHUB-LIFECYCLE.md.
        snap = {"result": "SKIPPED"}
        try:
            sp = subprocess.run([sys.executable, str(ROOT / "scripts" / "build-factory" / "bf_git_snapshot.py"),
                                 "--reason", args.reason or "beta_restart"],
                                capture_output=True, text=True, timeout=300)
            snap = json.loads((sp.stdout.strip().splitlines() or ["{}"])[-1])
        except Exception as exc:  # noqa: BLE001
            snap = {"result": "SNAPSHOT_ERROR", "error": exc.__class__.__name__}
        log_event({"event": "PRE_RELOAD_GIT_SNAPSHOT", "result": snap.get("result"),
                   "commit": snap.get("commit"), "pushed": snap.get("pushed")})

        uid = os.getuid()
        t0 = time.time()
        rc = subprocess.run(["launchctl", "kickstart", "-k", f"gui/{uid}/{LABEL}"],
                            capture_output=True, text=True).returncode
        STAMP.write_text(json.dumps({"at": now_iso(), "reason": args.reason,
                                     "caller": os.environ.get("BF_RELOAD_CALLER", ""),
                                     "before": before}) + "\n", encoding="utf-8")
        if rc != 0:
            log_event({"event": "RELOAD_KICKSTART_FAILED", "rc": rc})
            print(json.dumps({"result": "FAIL", "reason": f"launchctl rc={rc}"}))
            return 1

        ok_streak = 0
        deadline = t0 + args.wait_secs
        while time.time() < deadline:
            new = listeners(BETA_PORT)
            if len(new) == 1 and new != before and healthy():
                ok_streak += 1
                if ok_streak >= 3:
                    out = {"result": "UP", "before": before, "after": new,
                           "seconds_to_healthy": round(time.time() - t0, 1),
                           "prod_listening": PROD_PORT and 1297 in listeners(PROD_PORT)}
                    print(json.dumps(out)); log_event({"event": "RELOAD_UP", **out})
                    return 0
            else:
                ok_streak = 0
            time.sleep(0.5)
        out = {"result": "FAIL_NOT_HEALTHY", "before": before, "after": listeners(BETA_PORT),
               "note": "launchd KeepAlive owns recovery; no second kickstart"}
        print(json.dumps(out), file=sys.stderr); log_event({"event": "RELOAD_NOT_HEALTHY", **out})
        return 1


if __name__ == "__main__":
    sys.exit(main())
