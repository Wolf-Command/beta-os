#!/bin/bash
set -euo pipefail
ROOT="/Users/wolfterminal/beta-os"
STATE="$ROOT/state/wolf-intelligence/audit"
mkdir -p "$STATE"
PIDFILE="$STATE/owner-ui.pid"
LOG="$STATE/owner-ui.log"
cd "$ROOT"
export PYTHONUNBUFFERED=1 PATH="/opt/homebrew/bin:/usr/bin:/bin:$PATH"

if curl -fsS -m 1 http://127.0.0.1:8799/api/health >/dev/null 2>&1; then
  echo "already_healthy url=http://127.0.0.1:8799/"
  exit 0
fi

# Prefer launchd if loaded
if launchctl print "gui/$(id -u)/com.wolfcommand.wolf-intelligence-owner-ui" >/dev/null 2>&1; then
  launchctl kickstart -k "gui/$(id -u)/com.wolfcommand.wolf-intelligence-owner-ui" 2>/dev/null || true
  sleep 1
  if curl -fsS -m 2 http://127.0.0.1:8799/api/health >/dev/null 2>&1; then
    echo "kickstarted_launchd ok"
    exit 0
  fi
fi

# Fallback nohup
pkill -f 'python3 -m wolf_intelligence serve-ui' 2>/dev/null || true
sleep 0.5
# force free port holders for 8799 that are our module
for p in $(lsof -nP -iTCP:8799 -sTCP:LISTEN -t 2>/dev/null || true); do
  kill "$p" 2>/dev/null || true
done
sleep 0.3
nohup /opt/homebrew/bin/python3 -m wolf_intelligence serve-ui >>"$LOG" 2>&1 &
echo $! >"$PIDFILE"
for i in 1 2 3 4 5; do
  sleep 0.4
  if curl -fsS -m 1 http://127.0.0.1:8799/api/health >/dev/null 2>&1; then
    echo "started ok pid=$(cat "$PIDFILE") url=http://127.0.0.1:8799/"
    exit 0
  fi
done
echo "start_failed; see $LOG" >&2
tail -20 "$LOG" >&2 || true
exit 1
