#!/bin/bash
set -euo pipefail
ROOT="/Users/wolfterminal/beta-os"
PIDFILE="$ROOT/state/wolf-intelligence/audit/owner-ui.pid"
if [[ -f "$PIDFILE" ]]; then
  PID=$(cat "$PIDFILE" || true)
  if [[ -n "${PID:-}" ]]; then kill "$PID" 2>/dev/null || true; fi
  rm -f "$PIDFILE"
fi
pkill -f 'wolf_intelligence serve-ui' 2>/dev/null || true
echo stopped
