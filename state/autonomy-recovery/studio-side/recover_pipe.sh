#!/bin/bash
# Graceful quit → wait → kill -9 if needed → open -a Grok Bot.
# Rate limit: max 3 attempts / rolling 3600s. Latch file coordinates with NAS.
set -u
STATE_DIR="${MAC_REACH_ROOT:-/Users/wolfterminal/beta-os}/state/mac-reachability"
AUDIT="$STATE_DIR/logs/recover-pipe.audit.jsonl"
RATE="$STATE_DIR/recover-pipe.rate.json"
mkdir -p "$STATE_DIR/logs"
export TZ=Asia/Makassar
ts="$(date '+%Y-%m-%dT%H:%M:%S%z')"
EXACT="/Applications/Grok Bot.app/Contents/MacOS/Grok Bot"
SOURCE="${1:-manual}"

audit() {
  printf '{"ts_wita":"%s","event":"%s","source":"%s","detail":"%s"}\n' "$ts" "$1" "$SOURCE" "$2" >> "$AUDIT"
}

# rate limit
python3 - "$RATE" <<'PY' || exit 0
import json, sys, time
from pathlib import Path
p = Path(sys.argv[1])
now = time.time()
attempts = []
if p.exists():
    try:
        attempts = json.loads(p.read_text()).get("attempts", [])
    except Exception:
        attempts = []
attempts = [t for t in attempts if now - t < 3600]
if len(attempts) >= 3:
    print("RATE_LIMITED")
    raise SystemExit(2)
attempts.append(now)
p.write_text(json.dumps({"attempts": attempts}) + "\n")
print("RATE_OK", len(attempts))
PY
rc=$?
if [[ $rc -eq 2 ]]; then
  audit "rate_limited" "max_3_per_hour"
  echo "RATE_LIMITED"
  exit 0
fi

find_pid() {
  python3 - <<'PY'
import subprocess
exact="/Applications/Grok Bot.app/Contents/MacOS/Grok Bot"
out=subprocess.check_output(["ps","-ax","-o","pid=,command="], text=True, errors="replace")
for line in out.splitlines():
    line=line.strip()
    if not line: continue
    pid,_,comm=line.partition(" ")
    if comm==exact:
        print(pid); break
PY
}

pid="$(find_pid || true)"
audit "recover_start" "pid=${pid:-none}"

if [[ -n "${pid:-}" ]]; then
  # CONT first in case STOP'd so quit can run
  /bin/kill -CONT "$pid" 2>/dev/null || true
  /usr/bin/osascript -e 'tell application "Grok Bot" to quit' >/dev/null 2>&1 || true
  for i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 2
    np="$(find_pid || true)"
    [[ -z "${np:-}" ]] && break
  done
  np="$(find_pid || true)"
  if [[ -n "${np:-}" ]]; then
    audit "force_kill" "pid=$np"
    /bin/kill -9 "$np" 2>/dev/null || true
    sleep 2
  fi
fi

/usr/bin/open -a "Grok Bot"
sleep 3
newp="$(find_pid || true)"
audit "recover_done" "new_pid=${newp:-none}"
echo "RECOVER_PIPE_DONE new_pid=${newp:-none}"
