#!/usr/bin/env bash
# Mac Reachability — supervisor outline (SKELETON)
# Intended as LaunchAgent ProgramArguments entry.
# Loop: read heartbeat → detect → classify → recover → verify → audit → resume hint
set -euo pipefail

grok_pids() {
  python3 - "$@" << 'PY2'
import subprocess, sys
want = {
  "app": "/Applications/Grok Bot.app/Contents/MacOS/Grok Bot",
  "helper": "/Applications/Grok Bot.app/Contents/Frameworks/Grok Bot Helper.app/Contents/MacOS/Grok Bot Helper",
}
found = {k: "" for k in want}
out = subprocess.check_output(["ps", "-ax", "-o", "pid=,comm="], text=True)
for line in out.splitlines():
    line = line.strip()
    if not line:
        continue
    pid, _, comm = line.partition(" ")
    for key, exact in want.items():
        if comm == exact and not found[key]:
            found[key] = pid
which = sys.argv[1] if len(sys.argv) > 1 else "both"
if which == "both":
    print(found["app"])
    print(found["helper"])
else:
    print(found.get(which, ""))
PY2
}


ROOT="${MAC_REACH_ROOT:-/Users/wolfterminal/beta-os}"
SCRIPTS="${ROOT}/scripts/mac-reachability"
STATE="${ROOT}/state/mac-reachability"
AUDIT="${STATE}/audit.jsonl"
STALE_AFTER_SEC="${STALE_AFTER_SEC:-120}"
LOOP_SEC="${SUPERVISOR_LOOP_SEC:-20}"

mkdir -p "$STATE"
touch "$AUDIT"

audit() {
  local from="$1" to="$2" code="$3" detail="$4"
  local ts; ts="$(TZ=Asia/Makassar date '+%Y-%m-%dT%H:%M:%S%z')"
  printf '{"ts_wita":"%s","from":"%s","to":"%s","reason_code":"%s","detail":"%s","matt_contacted":false}\n' \
    "$ts" "$from" "$to" "$code" "$detail" >> "$AUDIT"
}

# Ensure heartbeat writer is running (LaunchAgent may co-manage)
# "${SCRIPTS}/heartbeat.sh" &  # prefer separate LaunchAgent

while true; do
  health="HEALTHY"
  connected=true  # Mac-local supervisor assumes host up; pipe visibility is box-side
  # Box-side Link still uses ListMachines; this Mac supervisor heals local daemons.

  # Real worker: exact Grok Bot.app binary + exact Helper. Not local-exec.
  pid="$(grok_pids app)"
  helper="$(grok_pids helper)"
  path_ok=false
  if [[ -f "${ROOT}/scripts/build-factory/bf_watch.py" ]]; then
    path_ok=true
  fi

  hb_age=0
  if [[ -f "${STATE}/heartbeat.json" ]]; then
    hb_age=0  # TODO: parse ts_wita age when applied
  else
    hb_age=9999
  fi

  if [[ -z "$pid" || -z "$helper" ]] || [[ "$path_ok" != true ]] || (( hb_age > STALE_AFTER_SEC )); then
    export CONNECTED=true
    export LOCAL_EXEC_PID=""
    export GROK_BOT_PID="$pid"
    export GROK_HELPER_PID="$helper"
    export PATH_PROVE_OK="$path_ok"
    export HEARTBEAT_AGE_SEC="$hb_age"
    export ACTIVE_PRESENT=false
    [[ -f "${ROOT}/state/build-factory/ACTIVE" ]] && export ACTIVE_PRESENT=true
    code="$("${SCRIPTS}/classify.sh")"
    primary="${code%%|*}"
    audit "HEALTHY" "RECOVERING" "$primary" "supervisor_detect"
    if "${SCRIPTS}/recover.sh"; then
      if "${SCRIPTS}/verify.sh"; then
        audit "RECOVERING" "HEALTHY" "$primary" "verify_pass_resume"
        # Resume: Peaches/box unpark when they see HEALTHY heartbeat/LKG
      else
        audit "RECOVERING" "DEGRADED" "$primary" "verify_fail"
      fi
    else
      rc=$?
      if [[ $rc -eq 2 ]]; then
        audit "RECOVERING" "BLOCKED" "CEILING_REACHED" "park_pipe_dependent_only"
      else
        audit "RECOVERING" "DEGRADED" "$primary" "recover_fail"
      fi
    fi
  fi
  sleep "$LOOP_SEC"
done
