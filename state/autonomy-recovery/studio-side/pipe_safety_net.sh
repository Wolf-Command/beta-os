#!/bin/bash
# Local safety net: if PIPE_DEAD continuously >= 20 minutes, recover once.
# Deliberately slower than NAS (5 min ticks) so NAS acts first.
set -u
HB="${WOLF_PIPE_HB:-/tmp/wolf-pipe-heartbeat.json}"
STATE="${MAC_REACH_ROOT:-/Users/wolfterminal/beta-os}/state/mac-reachability"
AUDIT="$STATE/logs/pipe-safety-net.audit.jsonl"
STAMP="$STATE/pipe-dead-since.epoch"
RECOVER="$STATE/../scripts/mac-reachability/recover_pipe.sh"
RECOVER="/Users/wolfterminal/beta-os/scripts/mac-reachability/recover_pipe.sh"
mkdir -p "$STATE/logs"
export TZ=Asia/Makassar
ts="$(date '+%Y-%m-%dT%H:%M:%S%z')"
now="$(date +%s)"
THRESHOLD=$((20*60))

audit() {
  printf '{"ts_wita":"%s","event":"%s","detail":"%s"}\n' "$ts" "$1" "$2" >> "$AUDIT"
}

if [[ ! -f "$HB" ]]; then
  audit "skip" "no_heartbeat_file"
  exit 0
fi

if grep -q '"pipe_ok": true' "$HB" 2>/dev/null; then
  rm -f "$STAMP"
  audit "pipe_ok" "clear_stamp"
  exit 0
fi

# pipe dead or unknown
if [[ ! -f "$STAMP" ]]; then
  printf '%s\n' "$now" > "$STAMP"
  audit "pipe_dead_start" "stamp=$now"
  exit 0
fi
since="$(cat "$STAMP" 2>/dev/null || echo "$now")"
age=$((now - since))
audit "pipe_dead_pending" "age_s=$age threshold=$THRESHOLD"
if (( age >= THRESHOLD )); then
  audit "safety_net_fire" "age_s=$age"
  bash "$RECOVER" "safety_net"
  # reset stamp so we don't loop immediately
  printf '%s\n' "$now" > "$STAMP"
fi
exit 0
