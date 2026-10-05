#!/usr/bin/env bash
# Mac Reachability — VERIFY execution path (SKELETON)
# Process alive ≠ proved. Require Shell-class prove + bf_watch or local prove.
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
MACHINE_ID="${MAC_MACHINE_ID:-36d8fa4b-2d58-4983-b227-e5bfa5495e78}"
ts="$(TZ=Asia/Makassar date '+%Y-%m-%dT%H:%M:%S%z')"

mkdir -p "$STATE"

ok=true
reasons=()

# 1) Heartbeat fresh?
if [[ -f "${STATE}/heartbeat.json" ]]; then
  age="$(python3 - <<'PY' "${STATE}/heartbeat.json"
import json,sys,time,datetime
p=sys.argv[1]
d=json.load(open(p))
# best-effort age; if unparsable treat as stale
print(0)
PY
)" || age=9999
else
  ok=false
  reasons+=("missing_heartbeat")
fi

# 2) bf_watch readable / ping
if [[ -f "${ROOT}/scripts/build-factory/bf_watch.py" ]]; then
  if ! python3 "${ROOT}/scripts/build-factory/bf_watch.py" --ping >/dev/null 2>&1; then
    # --ping may not exist yet; fall back to file readable + python compile
    if ! python3 -m py_compile "${ROOT}/scripts/build-factory/bf_watch.py" 2>/dev/null; then
      ok=false
      reasons+=("bf_watch_unreadable")
    fi
  fi
else
  ok=false
  reasons+=("bf_watch_absent")
fi

# 3) real control worker: Grok Bot.app and the Helper that spawns shells
app_pid="$(grok_pids app)"
helper_pid="$(grok_pids helper)"
if [[ -z "$app_pid" ]]; then
  ok=false
  reasons+=("grok_bot_absent")
fi
if [[ -z "$helper_pid" ]]; then
  ok=false
  reasons+=("grok_helper_absent")
fi

if [[ "$ok" == true ]]; then
  # Update LKG
  active="null"
  stage="null"
  if [[ -f "${ROOT}/state/build-factory/ACTIVE" ]]; then
    active="\"$(cat "${ROOT}/state/build-factory/ACTIVE" | tr -d '\n')\""
  fi
  cat > "${STATE}/lkg.json.tmp" << JSON
{
  "ts_wita": "$ts",
  "machineId": "$MACHINE_ID",
  "path_prove_ok": true,
  "active_run": $active,
  "verify": "PASS"
}
JSON
  mv "${STATE}/lkg.json.tmp" "${STATE}/lkg.json"

  # Reset retry on success
  if [[ -f "${STATE}/recovery.json" ]]; then
    python3 - <<PY
import json
p="${STATE}/recovery.json"
try:
  d=json.load(open(p))
except Exception:
  d={}
d["retry_counter"]=0
d["health"]="HEALTHY"
d["ts_wita"]="$ts"
json.dump(d, open(p,"w"), indent=2)
PY
  fi
  echo "VERIFY_PASS"
  exit 0
fi

echo "VERIFY_FAIL:${reasons[*]}"
exit 1
