#!/usr/bin/env bash
# Mac Reachability — bounded auto-recovery (SKELETON — NOT for Matt GUI)
# Box-side (Link) while DOWN: see BOX-SIDE-RETRY-PROTOCOL.md — no launchctl from box.
# Mac-side (this script): only after LaunchAgents installed on Studio.
# NEVER: ask Matt to open app / pkill as routine / reboot.
# Target Mac apply only when pipe can be healed locally via LaunchAgent.
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
CEILING="${RETRY_CEILING:-3}"
LABEL="${LAUNCH_LABEL:-com.wolf.mac-reachability.supervisor}"

mkdir -p "$STATE"
REC="${STATE}/recovery.json"

retry=0
if [[ -f "$REC" ]]; then
  retry="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("retry_counter",0))' "$REC" 2>/dev/null || echo 0)"
fi

if (( retry >= CEILING )); then
  echo "CEILING_REACHED — park pipe-dependent; continue independent; no Matt open-app" >&2
  exit 2
fi

retry=$((retry + 1))
# backoff: 15, 45, 120
case "$retry" in
  1) backoff=15 ;;
  2) backoff=45 ;;
  *) backoff=120 ;;
esac

ts="$(TZ=Asia/Makassar date '+%Y-%m-%dT%H:%M:%S%z')"
cat > "${REC}.tmp" << JSON
{
  "ts_wita": "$ts",
  "health": "RECOVERING",
  "retry_counter": $retry,
  "retry_ceiling": $CEILING,
  "backoff_sec": $backoff,
  "method": "launchctl_kickstart_${LABEL}",
  "matt_contacted": false
}
JSON
mv "${REC}.tmp" "$REC"

sleep "$backoff"

# Preferred: restart the proved control worker, not this supervisor.
KEEPALIVE="/Users/wolfterminal/.openclaw/workspace/wolf-system/scripts/grok-bot-keepalive.sh"
if [[ -x "$KEEPALIVE" ]]; then
  bash "$KEEPALIVE" || true
fi

# Also kickstart the wolf reachability labels. Never kickstart prod or beta.
if command -v launchctl >/dev/null 2>&1; then
  launchctl kickstart "gui/$(id -u)/com.wolfcommand.grok-bot-keepalive" 2>/dev/null || true
fi

echo "recover_attempt=$retry method=launchctl_kickstart"
exit 0
