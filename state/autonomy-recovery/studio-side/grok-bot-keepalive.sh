#!/bin/bash
# Periodic/kickstart keepalive. Recover only if app/helper missing OR pipe_dead.
set -u
RECOVER="/Users/wolfterminal/beta-os/scripts/mac-reachability/recover_pipe.sh"
HB="${WOLF_PIPE_HB:-/tmp/wolf-pipe-heartbeat.json}"

grok_pids() {
  python3 - <<'PY'
import subprocess
want={"app":"/Applications/Grok Bot.app/Contents/MacOS/Grok Bot",
      "helper":"/Applications/Grok Bot.app/Contents/Frameworks/Grok Bot Helper.app/Contents/MacOS/Grok Bot Helper"}
found={k:"" for k in want}
out=subprocess.check_output(["ps","-ax","-o","pid=,comm="], text=True)
for line in out.splitlines():
    line=line.strip()
    if not line: continue
    pid,_,comm=line.partition(" ")
    for key,exact in want.items():
        if comm==exact and not found[key]:
            found[key]=pid
print(found["app"])
print(found["helper"])
PY
}

read -r app_pid helper_pid < <(grok_pids | tr '\n' ' '; echo)
app_pid="${app_pid:-}"
helper_pid="${helper_pid:-}"

pipe_dead=0
if [[ -f "$HB" ]]; then
  if grep -q '"pipe_ok": false' "$HB" 2>/dev/null; then
    pipe_dead=1
  fi
fi

if [[ -z "$app_pid" || -z "$helper_pid" || "$pipe_dead" -eq 1 ]]; then
  bash "$RECOVER" "keepalive"
  exit 0
fi
exit 0
