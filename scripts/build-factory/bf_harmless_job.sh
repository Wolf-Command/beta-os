#!/bin/bash
# Harmless factory child — no Wolf app mutation. Writes artifact + EXIT line.
set -e
ROOT="/Users/wolfterminal/beta-os"
OUTDIR="$ROOT/state/build-factory/harmless-test"
mkdir -p "$OUTDIR"
LOG="${1:-$OUTDIR/job.log}"
ART="$OUTDIR/artifact.txt"
echo "HARMLESS_START $(TZ=Asia/Makassar date)" | tee -a "$LOG"
sleep 12
echo "harmless-factory-ok $(TZ=Asia/Makassar date)" > "$ART"
echo "HARMLESS_ARTIFACT=$ART" | tee -a "$LOG"
echo "EXIT:0" | tee -a "$LOG"
