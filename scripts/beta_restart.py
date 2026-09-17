#!/usr/bin/env python3
"""Safe Beta (:8788) restart via LaunchAgent only.

Refuses Production :8787. Never orphans nohup. KeepAlive=true on the plist —
use launchctl kickstart -k so the existing job is killed+restarted cleanly.
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time

LABEL = "net.wolfcommand.serve-beta"
BETA_PORT = 8788
PROD_PORT = 8787


def listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except OSError:
        return False


def lsof(port: int) -> str:
    try:
        return subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:  # noqa: BLE001
        return f"<lsof fail: {exc}>"


def main() -> int:
    ap = argparse.ArgumentParser(description="Restart Beta serve_beta via LaunchAgent")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wait-secs", type=float, default=8.0)
    args = ap.parse_args()

    # Hard refuse anything that smells like production serve
    prod = lsof(PROD_PORT)
    if "serve_beta" in prod.lower():
        print("REFUSE: serve_beta appears on :8787 (production lane). Abort.", file=sys.stderr)
        print(prod, file=sys.stderr)
        return 2

    uid = os.getuid()
    target = f"gui/{uid}/{LABEL}"
    cmd = ["launchctl", "kickstart", "-k", target]
    print("pre-restart :8788 listener:")
    print(lsof(BETA_PORT) or "<none>")
    print("cmd:", " ".join(cmd))
    if args.dry_run:
        print("dry-run — not executing")
        return 0

    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as exc:
        print(f"FAIL launchctl: {exc}", file=sys.stderr)
        return 1

    deadline = time.time() + args.wait_secs
    while time.time() < deadline:
        if listening(BETA_PORT):
            print("PASS Beta :8788 listening after kickstart")
            print(lsof(BETA_PORT))
            # Confirm prod still up / untouched
            if listening(PROD_PORT):
                print("PASS Production :8787 still listening (untouched)")
            else:
                print("WARN Production :8787 not listening — investigate (we did not touch it)")
            return 0
        time.sleep(0.4)

    print("FAIL :8788 did not come back within wait window", file=sys.stderr)
    print(lsof(BETA_PORT), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
