#!/bin/bash
set -u
export PATH="/Users/wolfterminal/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
cd /Users/wolfterminal/beta-os
LOG="state/bzg-daily-close/cursor-run-BZG-DAILY-CLOSE-TILL-EDC-1.log"
PROMPT_FILE="state/bzg-daily-close/CURSOR-PACK-BZG-DAILY-CLOSE-TILL-EDC-1.md"
mkdir -p "$(dirname "$LOG")"
{
  echo "CURSOR_START $(TZ=Asia/Makassar date '+%Y-%m-%dT%H:%M:%S') WITA"
  echo "MISSION=state/bzg-daily-close/CURSOR-PACK-BZG-DAILY-CLOSE-TILL-EDC-1.md"
  echo "HEAD=$(git rev-parse HEAD)"
  echo "HEAD_SHORT=$(git rev-parse --short HEAD)"
  echo "BRANCH=$(git branch --show-current)"
  echo "LAUNCH_MODE=shell_tool_background_tracked"
  echo "WRAPPER_PID=$$"
  echo "PACK=BZG-DAILY-CLOSE-TILL-EDC-1"
  echo "OWNER_ORDER=BZG-DAILY-CLOSE-TILL-EDC-20261002"
  echo "staff_ready=false"
  echo "human_commissioned=false"
  echo "telegram_recovery=TELEGRAM_SOURCE_INCOMPLETE"
  echo "prod=:8787 READ-ONLY"
  echo "credit_override=OWNER_ORDER"
} >> "$LOG"
PROMPT=$(cat "$PROMPT_FILE")
set +e
/Users/wolfterminal/.local/bin/cursor-agent -p --force --workspace /Users/wolfterminal/beta-os "$PROMPT" >> "$LOG" 2>&1
EC=$?
echo "CURSOR_SHELL_EXIT=$EC" >> "$LOG"
if [ "$EC" -eq 0 ]; then echo "EXIT:0" >> "$LOG"; else echo "EXIT:$EC" >> "$LOG"; fi
echo "CURSOR_DONE" >> "$LOG"
exit $EC
