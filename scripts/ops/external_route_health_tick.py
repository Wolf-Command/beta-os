#!/usr/bin/env python3
"""Operator / reliability watch tick — EXTERNAL-ROUTE-HEALTH (Beta only).

Usage:
  python3 scripts/ops/external_route_health_tick.py
  python3 scripts/ops/external_route_health_tick.py --json
  python3 scripts/ops/external_route_health_tick.py --no-recover
  python3 scripts/ops/external_route_health_tick.py --dry-run-recover

Never touches prod :8787. Never weakens auth.
Safe autorecovery: launchctl kickstart -k net.wolfcommand.atrium-finance-sidecar
only when :8790 is down and the LaunchAgent plist exists.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BETA_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BETA_ROOT / "scripts"))

from core import external_route_health as erh  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Probe Beta external finance routes + local Host Error deps"
    )
    ap.add_argument("--json", action="store_true", help="Print full JSON payload")
    ap.add_argument(
        "--no-recover",
        action="store_true",
        help="Skip launchctl kickstart even if sidecar down",
    )
    ap.add_argument(
        "--dry-run-recover",
        action="store_true",
        help="Log what kickstart would run without executing",
    )
    ap.add_argument(
        "--no-persist",
        action="store_true",
        help="Do not write state/ops/external-route-health-*.json",
    )
    args = ap.parse_args()

    payload = erh.run_probe(
        autorecover=not args.no_recover,
        dry_run_recover=args.dry_run_recover,
        persist=not args.no_persist,
    )
    overall = payload.get("overall") or {}
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        alert = payload.get("alert") or {}
        sidecar = ((payload.get("local_deps") or {}).get("sidecar_8790") or {}).get(
            "status"
        )
        print(
            f"external_route_health as_of={payload.get('as_of_wita')} "
            f"class={overall.get('class')} color={overall.get('color')} "
            f"sidecar={sidecar} "
            f"alert={alert.get('alert_id')} "
            f"transition_to_red={alert.get('transition_to_red')} "
            f"noise_suppressed={alert.get('noise_suppressed')}"
        )
        print(f"  summary: {overall.get('summary')}")
        for row in payload.get("external_routes") or []:
            klass = (row.get("classification") or {}).get("class")
            code = (row.get("http") or {}).get("status_code")
            print(f"  EXT {row.get('path')} → {code} {klass}")
        for row in payload.get("loopback_routes") or []:
            klass = (row.get("classification") or {}).get("class")
            code = (row.get("http") or {}).get("status_code")
            print(f"  LB  {row.get('path')} → {code} {klass}")
        rec = payload.get("autorecover")
        if rec and rec.get("attempted"):
            print(
                f"  autorecover attempted recovered={rec.get('recovered')} "
                f"rc={rec.get('rc')}"
            )
    # Exit 2 on RED CRITICAL so watches can alert; 0 otherwise.
    if overall.get("class") == erh.CLASS_RED:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
