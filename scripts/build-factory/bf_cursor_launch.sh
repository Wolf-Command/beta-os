#!/bin/bash
# Factory launcher. Args: log, prompt file, cursor pidfile.
# Does not echo the prompt or the process command line.
set -uo pipefail
cd /Users/wolfterminal/beta-os
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"
export CURSOR_AGENT_NO_INTERACTIVE=1
LOG="${1:?log}"
PROMPT_FILE="${2:?prompt}"
PIDFILE="${3:?pidfile}"
mkdir -p "$(dirname "$LOG")" "$(dirname "$PIDFILE")"
if [[ ! -s "$PROMPT_FILE" ]]; then
  echo "FATAL empty prompt file" >>"$LOG"
  echo "EXIT:2" >>"$LOG"
  exit 2
fi
PROMPT=$(cat "$PROMPT_FILE")
cursor-agent -p --force --workspace /Users/wolfterminal/beta-os "$PROMPT" >>"$LOG" 2>&1 &
APID=$!
echo "$APID" >"$PIDFILE"
echo "CURSOR_AGENT_PID=$APID" >>"$LOG"
wait "$APID"
EC=$?
echo "EXIT:$EC" >>"$LOG"
echo "CURSOR_DONE" >>"$LOG"
# Auto-dispatch on completion (Owner P0 5 Oct 2026): a detached supervisor tick runs a few
# seconds after this wrapper exits, so the next eligible slice starts without waiting for
# launchd's 5-minute interval. bf_supervisor serialises ticks with a flock.
( sleep 8; /opt/homebrew/bin/python3 /Users/wolfterminal/beta-os/scripts/build-factory/bf_supervisor.py \
    >>/Users/wolfterminal/beta-os/state/build-factory/on-exit-ticks.log 2>&1 ) </dev/null >/dev/null 2>&1 &
disown || true
exit "$EC"
