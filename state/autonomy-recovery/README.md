# Autonomy recovery (2026-10-06 P0)

Survive Studio / Grok Bot pipe failure without Matt as the recovery mechanism.

## Components
1. `nas-supervisor/watcher.py` — always-on NAS supervisor (heartbeat miss → recover-watchdog → backoff → escalate only if no alt worker).
2. `worker-failover/failover.py` — if Studio down, repo-eligible work → `cursor_cloud_agent` with idempotency lock.
3. `evidence/` — INCIDENT-20261005-2255 + probes + drill results.
4. `patches/` — Phase 6 truthful relabel (BUILT / SYNTHETIC TESTED).

## Deploy (requires NAS path — not available from box tonight)
- Copy `nas-supervisor/watcher.py` to NAS wolf-recovery dir.
- Wire real Transport using existing `tailscale nc` + on-NAS key (do not copy key off NAS).
- Schedule every 60s (tighter than 5 min DSM task) or keep 5 min and set miss_threshold accordingly.
- Persist state+audit on NAS; mirror sanitized JSON into `wolfcommand/beta-os` `state/autonomy-recovery/`.

## Box limitation
This box has no Tailscale and no recovery key (by design). It cannot invoke NAS→Studio tonight.
