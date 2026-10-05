#!/bin/bash
# Night watch until next 06:55 WITA — safe shadow ticks + UI health
set -euo pipefail
ROOT=/Users/wolfterminal/beta-os
cd "$ROOT"
LOG=$ROOT/state/wolf-intelligence/audit/night-watch.log
END_EPOCH=$(/opt/homebrew/bin/python3 - <<'PY'
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Makassar')
now=datetime.now(TZ)
target=now.replace(hour=6, minute=55, second=0, microsecond=0)
if target <= now:
    target = target + timedelta(days=1)
print(int(target.timestamp()))
print(target.isoformat(), file=__import__('sys').stderr)
PY
)
echo "night_watch start $(date) end_epoch=$END_EPOCH" | tee -a "$LOG"
while true; do
  NOW=$(date +%s)
  if [[ "$NOW" -ge "$END_EPOCH" ]]; then
    echo "night_watch morning_gate $(date)" | tee -a "$LOG"
    /opt/homebrew/bin/python3 -m wolf_intelligence overnight-tick >>"$LOG" 2>&1 || true
    /opt/homebrew/bin/python3 -m wolf_intelligence stats >>"$LOG" 2>&1 || true
    curl -fsS http://127.0.0.1:8799/api/health >>"$LOG" 2>&1 || echo UI_DOWN >>"$LOG"
    echo DONE >>"$LOG"
    break
  fi
  /opt/homebrew/bin/python3 -m wolf_intelligence overnight-tick >>"$LOG" 2>&1 || echo TICK_FAIL $(date) >>"$LOG"
  curl -fsS http://127.0.0.1:8799/api/health >/dev/null 2>&1 || ./wolf_intelligence/bin/start_owner_ui.sh >>"$LOG" 2>&1 || true
  echo "tick_ok $(date) remain_s=$((END_EPOCH - NOW))" >>"$LOG"
  sleep 1800
done
