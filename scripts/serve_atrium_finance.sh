#!/bin/bash
# Loopback sidecar for Zayen's Atrium Finance. Does not print secrets.
set -euo pipefail
ROOT="/Users/wolfterminal/atrium-finance"
SECRETS="$ROOT/data/beta/secrets.env"
mkdir -p "$ROOT/data/beta"
if [ ! -f "$SECRETS" ]; then
  umask 077
  {
    printf 'SESSION_SECRET=%s\n' "$(openssl rand -hex 32)"
    printf 'WOLF_ASSERTION_SECRET=%s\n' "$(openssl rand -hex 32)"
  } > "$SECRETS"
fi
chmod 600 "$SECRETS"
set -a
# shellcheck disable=SC1090
source "$SECRETS"
set +a
export ATRIUM_BETA_MOUNT=1
export VITE_BETA_MOUNT=1
export VITE_BASE=/amg/finance/
export PORT=8790
export DATABASE_FILE="$ROOT/data/beta/atrium.sqlite"
export ATRIUM_CHART_SEED="/Users/wolfterminal/beta-os/scripts/core/data/atrium_coa_seed.json"
cd "$ROOT"
exec npx tsx server.ts
