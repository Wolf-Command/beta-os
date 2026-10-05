#!/usr/bin/env python3
"""Authenticated Daily Close prove against DEPLOYED Beta (phone-size).

READY requirements (all required; Matt = HUMAN COMMISSIONING only):
  deployed Beta · authenticated route · real rendered phone-size workflow ·
  persistence · reload · no raw errors · all six steps · submit result ·
  protected historical records unchanged.

Does NOT declare HUMAN READY / staff_ready from an isolated copy alone.
Uses bf_auth_harness (CF-sim JWT) — no Matt Cloudflare session.

Defer full public run until human-test window ends and disk is safe.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path("/Users/wolfterminal/beta-os").resolve()
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "build-factory"))

from bf_auth_harness import DEFAULT_EMAIL, authenticated_session, smoke_identity  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default=DEFAULT_EMAIL)
    ap.add_argument("--smoke-only", action="store_true", help="Auth smoke against :8788 only")
    ap.add_argument("--full", action="store_true", help="Full six-step phone prove (post-22:00)")
    args = ap.parse_args()
    if args.smoke_only or not args.full:
        r = smoke_identity(args.email)
        print(json.dumps({"phase": "smoke", **r, "staff_ready": False, "human_ready": False}, indent=2))
        return 0 if r.get("ok") else 2
    # Full prove is intentionally a separate follow-up after reload window.
    print(json.dumps({
        "phase": "full",
        "ok": False,
        "reason": "full_prove_deferred_until_after_human_test_window_and_disk_safe",
        "staff_ready": False,
        "human_ready": False,
        "requires": [
            "deployed Beta after gated reload",
            "authenticated route via bf_auth_harness",
            "iPhone 14 rendered six-step",
            "persistence + reload",
            "no raw errors",
            "submit result",
            "protected closes unchanged",
        ],
    }, indent=2))
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
