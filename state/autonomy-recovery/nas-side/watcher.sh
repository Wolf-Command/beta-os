#!/bin/bash
# NAS supervisor v2 dispatcher (2026-10-06). DSM task 7 calls this path.
# Real Studio target 100.113.26.51:2222; forced-command recover-watchdog (not dry-run).
# miss_threshold=1 matches prior watcher.sh (fire on first GROK_APP NONE).
set -u
cd "/var/services/homes/Mr Wolf/.ssh/wolf-recovery" || exit 0
export TZ=Asia/Makassar
exec /usr/bin/python3 run_watcher_v2.py --once --label live --miss-threshold 1 \
  --probe-host 100.113.26.51 --probe-port 2222
