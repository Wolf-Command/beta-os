# Evidence index — autonomy recovery 2026-10-06 (WITA)

| Proof item | File | Verdict |
|---|---|---|
| Studio rejoin after overnight outage | `STUDIO-REJOIN-20261006.json` | LIVE PROVED |
| Root cause (pipe dead, app alive; not system sleep) | `ROOT-CAUSE-20261005-2255.json` | LIVE PROVED |
| Pipe signal design (state T + AppleEvent) | `PIPE-SIGNAL-20261006.json` | LIVE PROVED |
| Conn-state log parser (WCS priorState) historical replay | `CONN-STATE-REPLAY-20261006.json` | REPLAY PROVED |
| Live inject of reconnecting without HID/Matt | (none — unsafe) | UNPROVED |
| NAS supervisor deploy + DSM task 7 | `NAS-SUPERVISOR-DEPLOY-20261006.json` | LIVE PROVED |
| NAS detects PIPE_DEAD while PID present | `LIVE-RECOVERY-TEST-20261006.json` | LIVE PROVED |
| NAS invokes recover-watchdog ForceCommand | `LIVE-RECOVERY-TEST-20261006.json` + studio `audits/wolfrecover-audit-excerpt.txt` | LIVE PROVED |
| Control path auto-returns (quit/relaunch) | `LIVE-RECOVERY-TEST-20261006.json` | LIVE PROVED |
| Safety net did not fire first | studio `audits/pipe-safety-net.audit.jsonl` | LIVE PROVED |
| Backoff latch + rearm | `LIVE-RECOVERY-TEST-20261006.json` + `nas-side/watcher_v2.live.state.json` | LIVE PROVED |
| Backoff schedule 60/180/600/1800 | `tests/test_recovery_architecture.py` | UNIT TESTED |
| PIPE_DEAD parse (PID present) | `tests/test_recovery_architecture.py` | UNIT TESTED |
| Duplicate work prevention NOOP | `work-store-live.json` + `failover-live.audit.jsonl` | LIVE PROVED |
| Single COMPLETED work item @ de256dad | `work-store-live.json` | LIVE PROVED |
| Worker registry UNAVAILABLE→AVAILABLE | `worker-registry.json` | LIVE PROVED |
| Matt not required for recovery | `LIVE-RECOVERY-TEST-20261006.json` | LIVE PROVED |
| NAS no false-positive after conn_state (2 ticks) | `nas-side/watcher_v2.live.audit.excerpt.jsonl` | LIVE PROVED |
| Box tailnet observer join | `BOX-TAILNET-JOIN-20261006.json` | LIVE PROVED (if present) |
| Overnight incident narrative (pre-Studio Shell) | `INCIDENT-20261005-2255.json` | PARTIAL (updated by ROOT-CAUSE) |

