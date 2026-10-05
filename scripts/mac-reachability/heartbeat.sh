#!/usr/bin/env bash
# Mac Reachability — heartbeat writer (SKELETON — do not install/apply while pipe DOWN)
# Target Mac: /Users/wolfterminal/beta-os/scripts/mac-reachability/heartbeat.sh
# Writes state/mac-reachability/heartbeat.json; updates LKG pointer on successful path prove.
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
STATE="${ROOT}/state/mac-reachability"
INTERVAL="${HEARTBEAT_INTERVAL_SEC:-30}"
MACHINE_ID="${MAC_MACHINE_ID:-36d8fa4b-2d58-4983-b227-e5bfa5495e78}"

mkdir -p "$STATE"

path_prove() {
  # Process alive ≠ path proved. Prefer bf_watch readable OR local Shell self-check.
  if command -v python3 >/dev/null 2>&1 && [[ -f "${ROOT}/scripts/build-factory/bf_watch.py" ]]; then
    python3 "${ROOT}/scripts/build-factory/bf_watch.py" --ping >/dev/null 2>&1 && return 0
  fi
  # Fallback: trivial local prove (Mac-side only). Box must never invent this.
  return 1
}

local_exec_pid() {
  # Retired name. Kept so old readers see null, not a guessed pid.
  true
}

grok_bot_running() {
  pgrep -f 'Grok Bot' >/dev/null 2>&1 && echo true || echo false
}

while true; do
  ts="$(TZ=Asia/Makassar date '+%Y-%m-%dT%H:%M:%S%z')"
  pid=""
  gb="$(grok_bot_running)"
  gpid="$(grok_pids app)"
  hpid="$(grok_pids helper)"
  prove=false
  if path_prove; then prove=true; fi
  health="STALE"
  if [[ -n "$gpid" && -n "$hpid" ]]; then health="HEALTHY"
  elif [[ -n "$gpid" || -n "$hpid" ]]; then health="DEGRADED"
  else health="BLOCKED"; fi
  # Note: outer supervisor may override to RECOVERING during recover.sh

  cat > "${STATE}/heartbeat.json.tmp" << JSON
{
  "ts_wita": "$ts",
  "machineId": "$MACHINE_ID",
  "local_exec_pid": null,
  "grok_bot_pid": ${gpid:-null},
  "grok_helper_pid": ${hpid:-null},
  "grok_bot_running": $gb,
  "path_prove_ok": $prove,
  "health_hint": "$health",
  "lkg_pointer": "${STATE}/lkg.json"
}
JSON
  mv "${STATE}/heartbeat.json.tmp" "${STATE}/heartbeat.json"

  if [[ "$prove" == true ]]; then
    # Soft LKG touch — full LKG write belongs in verify.sh after recover
    :
  fi
  sleep "$INTERVAL"
done
