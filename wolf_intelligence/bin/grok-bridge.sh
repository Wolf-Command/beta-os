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
export WOLF_INTELLIGENCE_GROK_DOORBELL="${WOLF_INTELLIGENCE_GROK_DOORBELL:-github}"
unset WOLF_INTELLIGENCE_LIVE_SUBMIT || true
cd "$RUNTIME"
exec /opt/homebrew/bin/python3 -m wolf_intelligence grok-bridge "$@"
