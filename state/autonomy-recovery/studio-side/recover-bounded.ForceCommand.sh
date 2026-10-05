#!/bin/bash
set -u
AUDIT="/var/wolfrecover/logs/audit.log"
ts="$(TZ=Asia/Makassar date '+%Y-%m-%dT%H:%M:%S%z')"
cmd="${SSH_ORIGINAL_COMMAND:-status}"
safe="$(printf '%s' "$cmd" | tr '\n' ' ' | cut -c1-180)"
audit() {
  printf '%s cmd=%s result=%s\n' "$ts" "$safe" "$1" >> "$AUDIT"
}
case "$cmd" in
  status)
    python3 - << 'PY'
import subprocess
exact="/Applications/Grok Bot.app/Contents/MacOS/Grok Bot"
helper="/Applications/Grok Bot.app/Contents/Frameworks/Grok Bot Helper.app/Contents/MacOS/Grok Bot Helper"
out=subprocess.check_output(["ps","-ax","-o","pid=,command="], text=True, errors="replace")
app="NONE"
hn=0
flags={"supervisor":"DOWN","heartbeat":"DOWN","keepalive":"DOWN"}
for line in out.splitlines():
    line=line.strip()
    if not line:
        continue
    pid,_,comm=line.partition(" ")
    if comm==exact and app=="NONE":
        app=pid
    elif comm==helper or comm.startswith(helper+" "):
        hn+=1
    if "mac-reachability/supervisor.sh" in comm:
        flags["supervisor"]="UP"
    if "mac-reachability/heartbeat.sh" in comm:
        flags["heartbeat"]="UP"
    if "grok-bot-keepalive.sh" in comm:
        flags["keepalive"]="UP"
print("GROK_APP %s HELPERS %d" % (app, hn))
print("WATCHDOG supervisor=%s heartbeat=%s keepalive=%s" % (flags["supervisor"], flags["heartbeat"], flags["keepalive"]))
PY
    prod="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8787/api/health || echo ERR)"
    beta="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8788/api/health || echo ERR)"
    prod_pid="$(ps -p 15975 -o pid= 2>/dev/null | tr -d ' ' || true)"
    audit "status"
    echo "STATUS host=$(hostname)"
    echo "PROD_HEALTH ${prod} PROD_PID ${prod_pid:-missing}"
    echo "BETA_HEALTH ${beta}"
    ;;
  recover-watchdog)
    uid_gui="501"
    launchctl kickstart "gui/${uid_gui}/com.wolf.mac-reachability.supervisor" || true
    launchctl kickstart "gui/${uid_gui}/com.wolf.mac-reachability.heartbeat" || true
    launchctl kickstart "gui/${uid_gui}/com.wolfcommand.grok-bot-keepalive" || true
    audit "recover-watchdog"
    echo "RECOVER_WATCHDOG_DONE"
    ;;
  *)
    audit "DENIED"
    echo "DENIED"
    exit 1
    ;;
esac
