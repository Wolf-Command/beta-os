# BACKUP-STALE-DIAG — 1 Oct 2026 WITA

Generated: `2026-10-01T09:45:39+08:00` · Peaches-executor · Prod :8787 untouched (pid 15975)

## Verdict
**STALE TELEMETRY — not backup failure.** Fixed by refreshing monitoring-snapshot.

## Evidence
| Fact | Value |
|---|---|
| Pulse before | PARTIAL_STALE_ATRIUM (atrium snap STALE) |
| Snapshot source | `/Users/wolfterminal/monitoring-snapshot/manifest.json` |
| Snapshot age rule | STALE if `generated_at` > 90 minutes |
| Manifest before | `2026-09-30T23:45:04+08:00` (~10h stale at 09:37) |
| Staged backup_status before | `last_run=2026-09-30T02:00:01` |
| **Live** backup_status | `/Users/wolfterminal/.openclaw/state/backup_status.json` |
| Live last_run | **2026-10-01T02:00:01** local_ok=true b2_ok=true secrets_ok=true files=8173 |
| B2 daily-backups | `wolf-secrets-20261001.tar.gz.gpg` present |
| Nightly snapshot job | `com.wolfcommand.monitoring-snapshot` @ 23:45 WITA only |
| Fix applied | Ran `stage_monitoring_snapshot.py` → manifest `2026-10-01T09:42:41+08:00` |
| Pulse after | atrium snap **PRESENT** age≈0 · backup PRESENT · precise_state **PARTIAL** (pipe AMBER only) |

## Root cause
Owner pulse / BACKUP-HEALTH-1 reads atrium RO **staging** (`monitoring-snapshot`), not live `~/.openclaw/state/backup_status.json`. Nightly staging @ 23:45 left daytime pulse reading a >90m-old manifest even though Oct 1 02:00 backup succeeded.

## Residual
- Pipe `ORIGIN_REACHABLE/AMBER` = Cloudflare Access on unauth probe (expected) — **not** backup failure.
- Restore drill still historical / NOT freshly re-run (OPTIONAL / NON-GATING).

## Applied
- monitoring-snapshot refreshed
- DESKTOP-GATE de-blocks BACKUP-STALE-ATRIUM
- staff_ready=false · desktop_gate_ready=false · no Exit Report · no WOLF DESKTOP READY
