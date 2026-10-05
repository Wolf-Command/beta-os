#!/bin/bash
set -u
STATE="/Users/wolfterminal/beta-os/state/mac-reachability"
OUT="$STATE/DRILL-20261003-UNATTENDED.json"
sleep 20
ts() { TZ=Asia/Makassar date '+%Y-%m-%dT%H:%M:%S%z'; }
app_pid() {
python3 - << 'PY'
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
}
helper_n() {
python3 - << 'PY'
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
}
old="$(app_pid)"
started="$(ts)"
health_before="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8787/api/health || echo ERR)"
if [[ -n "${old:-}" ]]; then
  /bin/kill "$old" 2>/dev/null || true
  sleep 2
  if ps -p "$old" >/dev/null 2>&1; then /bin/kill -9 "$old" 2>/dev/null || true; fi
fi
new=""
detected=""
for i in $(seq 1 40); do
  sleep 2
  cur="$(app_pid)"
  if [[ -n "$cur" && "$cur" != "$old" ]]; then
    new="$cur"
    detected="$(ts)"
    break
  fi
done
helper="$(helper_n)"
prod="$(ps -p 15975 -o pid= 2>/dev/null | tr -d ' ' || true)"
health_after="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8787/api/health || echo ERR)"
beta_after="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8788/api/health || echo ERR)"
pass=false
if [[ -n "$new" && "$helper" != "0" && "$prod" == "15975" ]]; then pass=true; fi
cat > "$OUT" << JSON
{
  "started_wita": "$started",
  "detected_wita": "$detected",
  "finished_wita": "$(ts)",
  "killed_pid": "${old}",
  "new_pid": "${new}",
  "helper_count_after": "${helper}",
  "prod_pid_15975_after": "${prod}",
  "prod_health_before": "${health_before}",
  "prod_health_after": "${health_after}",
  "beta_health_after": "${beta_after}",
  "keepalive_called_by_drill": false,
  "pass": ${pass}
}
JSON
launchctl bootout "gui/$(id -u)/com.wolf.mac-reachability.drill-unattended" 2>/dev/null || true
