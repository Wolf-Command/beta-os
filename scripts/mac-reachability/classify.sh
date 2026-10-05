#!/usr/bin/env bash
# Mac Reachability — classify failure reason code (SKELETON)
# stdin/env: CONNECTED, LOCAL_EXEC_PID, PATH_PROVE_OK, HEARTBEAT_AGE_SEC, RETRY_COUNT, CEILING, ACTIVE_PRESENT, QUEUE_HAS_WORK
# stdout: reason_code
set -euo pipefail

CONNECTED="${CONNECTED:-false}"
LOCAL_EXEC_PID="${LOCAL_EXEC_PID:-}"
PATH_PROVE_OK="${PATH_PROVE_OK:-false}"
HEARTBEAT_AGE_SEC="${HEARTBEAT_AGE_SEC:-9999}"
STALE_AFTER_SEC="${STALE_AFTER_SEC:-120}"
RETRY_COUNT="${RETRY_COUNT:-0}"
CEILING="${RETRY_CEILING:-3}"
ACTIVE_PRESENT="${ACTIVE_PRESENT:-false}"
QUEUE_HAS_WORK="${QUEUE_HAS_WORK:-false}"
NEEDS_MATT_CLASS="${NEEDS_MATT_CLASS:-}"

if [[ -n "$NEEDS_MATT_CLASS" ]]; then
  echo "$NEEDS_MATT_CLASS"
  exit 0
fi

if (( RETRY_COUNT >= CEILING )); then
  echo "CEILING_REACHED"
  exit 0
fi

if [[ "$CONNECTED" != "true" ]]; then
  code="PIPE_DISCONNECTED"
elif [[ -z "$LOCAL_EXEC_PID" ]]; then
  code="LOCAL_EXEC_DEAD"
elif [[ "$PATH_PROVE_OK" != "true" ]]; then
  code="HALF_DEAD_PATH"
elif (( HEARTBEAT_AGE_SEC > STALE_AFTER_SEC )); then
  code="STALE_HEARTBEAT"
else
  code="PIPE_DISCONNECTED"
fi

# Annotate factory coupling (secondary tag printed after primary for audit parsers)
if [[ "$ACTIVE_PRESENT" == "true" ]]; then
  echo "${code}|FACTORY_ACTIVE_DURING_FAIL"
elif [[ "$QUEUE_HAS_WORK" == "true" ]]; then
  echo "${code}|IDLE_WITH_WORK_DURING_FAIL"
else
  echo "$code"
fi
