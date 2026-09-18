# FACTORY SUPERVISOR CALENDAR-FREE PROOF — 2026-09-19

## Historical disappearance

Result **FAIL** recorded in `FACTORY-DISAPPEARANCE-TEST-2026-09-18-19.md`. Not rewritten.

## Root cause

Grok routine `build-factory-watch` cron day-of-week `1-5`. Saturday silence.

## Repair

| Layer | Change |
| --- | --- |
| Software | `bf_supervisor.py` — ACTIVE-only, calendar-blind |
| OS | LaunchAgent `net.wolfcommand.build-factory-supervisor` StartInterval 300, no calendar |
| Agent wake | Routine schedule `*/5 * * * *` all days; quiet if inactive |

## Deterministic tests

`python3 scripts/tests/test_build_factory_supervisor.py` → **PASS=22 FAIL=0**

Proved: Saturday advance · Sunday advance · weekday advance · inactive IDLE · EXIT:0 ADVANCE · dead/no-exit RECOVER_INSPECT · retry ceiling BLOCKED · idempotent · Matt not in tick() signature · blocked lane alternate · LaunchAgent has no Weekday calendar.

## Real Beta harmless mission (Saturday 19 Sep 07:16 WITA)

- Run `BF-supervisor-weekend-prove-20260919`
- Child: `bf_harmless_job.sh` → EXIT:0
- Supervisor tick → ADVANCE → stage GROK_REVIEW
- WAKE `require_matt: false`
- No Matt status input used
- ACTIVE cleared after DONE; next tick IDLE

## Not claimed

Peaches still executes Grok judgment after WAKE. The claim is: advancement to GROK_REVIEW and recovery WAKE no longer depend on weekday or Matt status.
