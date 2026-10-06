#!/bin/bash
# Studio entry point for the Grok work bridge (what a Grok routine runs over the machine pipe).
#   grok-bridge.sh claim    <work_item_id> --nonce <nonce> --claimant <id>
#   grok-bridge.sh renew    <work_item_id> --lease <lease_id>
#   grok-bridge.sh complete <work_item_id> --lease <lease_id> (--result-file <path> | --result-stdin) [--evidence-file <path>]
#   grok-bridge.sh fail     <work_item_id> --lease <lease_id> --reason <text> [--retryable]
#   grok-bridge.sh status   <work_item_id>
# stdout is exactly one JSON object. Exit 0 ok, 3 protocol rejection, 2 bad input/not found, 1 internal error.
# WOLF_INTELLIGENCE_STATE_ROOT must be set explicitly (no silent default to live state). bash 3.2 compatible.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
RUNTIME="${WI_GROK_BRIDGE_RUNTIME:-$(cd "$HERE/../.." && pwd)}"
if [ -z "${WOLF_INTELLIGENCE_STATE_ROOT:-}" ]; then
  echo '{"ok": false, "code": "STATE_ROOT_REQUIRED", "message": "set WOLF_INTELLIGENCE_STATE_ROOT"}'
  exit 2
fi
CMD="${1:-}"
case "$CMD" in
  claim|renew|complete|fail|status) ;;
  *)
    echo '{"ok": false, "code": "NOT_ALLOWED_FOR_WORKER"}'
    exit 2
    ;;
esac
export WOLF_INTELLIGENCE_GROK_DOORBELL="${WOLF_INTELLIGENCE_GROK_DOORBELL:-github}"
cd "$RUNTIME"
ENV_ARGS=()
for var in HOME USER LOGNAME PATH LANG TMPDIR WOLF_INTELLIGENCE_STATE_ROOT \
  WOLF_INTELLIGENCE_GROK_DOORBELL WOLF_INTELLIGENCE_GROK_DOORBELL_REPO \
  WOLF_INTELLIGENCE_GROK_DOORBELL_ASSIGNEE WOLF_INTELLIGENCE_GROK_AUDIT_KEY_FILE \
  GROK_BRIDGE_PYTHON; do
  eval "val=\${$var-}"
  if [ -n "$val" ]; then
    ENV_ARGS+=("$var=$val")
  fi
done
ENV_ARGS+=("SHELL=/bin/bash")
PYTHON="${GROK_BRIDGE_PYTHON:-python3}"
exec /usr/bin/env -i "${ENV_ARGS[@]}" "$PYTHON" -m wolf_intelligence grok-bridge "$@"
