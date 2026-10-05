#!/bin/bash
set -u
STATE="/Users/wolfterminal/beta-os/state/mac-reachability"
OUT="$STATE/DRILL-20261003.json"
KEEP="/Users/wolfterminal/.openclaw/workspace/wolf-system/scripts/grok-bot-keepalive.sh"
sleep 25
ts() { TZ=Asia/Makassar date '+%Y-%m-%dT%H:%M:%S%z'; }
prod_before="$(ps -ax -o pid=,comm= | awk '$2 ~ /Python/ && $1==15975 {print 15975}')"
# exact main pid
app_pid="$(python3 - << 'PY'
import subprocess
exact="/Applications/Grok Bot.app/Contents/MacOS/Grok Bot"
out=subprocess.check_output(["ps","-ax","-o","pid=,comm="], text=True)
for line in out.splitlines():
    line=line.strip()
    if not line: continue
    pid,_,comm=line.partition(" ")
    if comm==exact:
        print(pid); break
PY
)"
helper_before="$(python3 - << 'PY'
import subprocess
exact="/Applications/Grok Bot.app/Contents/Frameworks/Grok Bot Helper.app/Contents/MacOS/Grok Bot Helper"
out=subprocess.check_output(["ps","-ax","-o","pid=,comm="], text=True)
n=0
for line in out.splitlines():
    line=line.strip()
    if not line: continue
    pid,_,comm=line.partition(" ")
    if comm==exact: n+=1
print(n)
PY
)"
health_before="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8787/api/health || echo ERR)"
beta_before="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8788/api/health || echo ERR)"
started="$(ts)"
if [[ -n "${app_pid:-}" ]]; then
  /bin/kill "$app_pid" 2>/dev/null || true
  sleep 3
  if ps -p "$app_pid" >/dev/null 2>&1; then
    /bin/kill -9 "$app_pid" 2>/dev/null || true
    sleep 1
  fi
fi
bash "$KEEP" || true
new_pid=""
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  sleep 2
  new_pid="$(python3 - << 'PY'
import subprocess
exact="/Applications/Grok Bot.app/Contents/MacOS/Grok Bot"
out=subprocess.check_output(["ps","-ax","-o","pid=,comm="], text=True)
for line in out.splitlines():
    line=line.strip()
    if not line: continue
    pid,_,comm=line.partition(" ")
    if comm==exact:
        print(pid); break
PY
)"
  if [[ -n "$new_pid" && "$new_pid" != "${app_pid:-}" ]]; then
    break
  fi
  new_pid=""
done
helper_after="$(python3 - << 'PY'
import subprocess
exact="/Applications/Grok Bot.app/Contents/Frameworks/Grok Bot Helper.app/Contents/MacOS/Grok Bot Helper"
out=subprocess.check_output(["ps","-ax","-o","pid=,comm="], text=True)
n=0
for line in out.splitlines():
    line=line.strip()
    if not line: continue
    pid,_,comm=line.partition(" ")
    if comm==exact: n+=1
print(n)
PY
)"
prod_after="$(ps -p 15975 -o pid= 2>/dev/null | tr -d ' ' || true)"
health_after="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8787/api/health || echo ERR)"
beta_after="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8788/api/health || echo ERR)"
pass=false
if [[ -n "$new_pid" && "$new_pid" != "${app_pid:-}" && "$helper_after" != "0" && "$prod_after" == "15975" ]]; then
  pass=true
fi
cat > "$OUT" << JSON
{
  "started_wita": "$started",
  "finished_wita": "$(ts)",
  "killed_pid": "${app_pid:-}",
  "helper_count_before": "${helper_before}",
  "new_pid": "${new_pid}",
  "helper_count_after": "${helper_after}",
  "prod_pid_15975_after": "${prod_after}",
  "prod_health_before": "${health_before}",
  "prod_health_after": "${health_after}",
  "beta_health_before": "${beta_before}",
  "beta_health_after": "${beta_after}",
  "pass": ${pass}
}
JSON
launchctl bootout "gui/$(id -u)/com.wolf.mac-reachability.drill-once" 2>/dev/null || true
