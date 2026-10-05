# Box-side heartbeat / retry (Link OWN)

When Peaches/pipe-watch hands **OWN BOUNDED AUTO-RECOVERY** and Studio `connected=false`:

## Loop (ceiling 3)

| Retry | Backoff before | Actions |
|-------|----------------|---------|
| 0 | 0s | ListMachines + Shell `echo PROVE_OK; hostname; date; whoami` |
| 1 | 20s | same |
| 2 | 45s | same |
| 3 | 120s | same — then STOP thrash |

## GREEN only if BOTH

1. `ListMachines` → `connected=true` for machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`
2. Shell prove returns `PROVE_OK` + hostname `Wolfs-Mac-Studio.local` (or current Studio hostname)

Process listed ≠ GREEN. Vendor “desktop must be open” = A-class daemon/app, **not** proven B-class.

## On FAIL after ceiling

- File `state/recovery-attempt-YYYYMMDD-HHMM.json`
- `bounded_restart.method = NONE_AVAILABLE` until LaunchAgent commission or authorised OOB actuator
- Continue LaunchAgent design on box; **no Matt open-app escalate**
- Report Peaches: FAIL + A-class + evidence path; silent to Matt
- On later GREEN: MAC-APPLY package → prove ×2 → ping Peaches + Pulse (+ Vesper if waiting)

## Never

- Invent GREEN
- Reboot / power-cycle / Reset Peaches PC
- Treat Update Grok Bot as the fix
- Ask Matt Cmd-Q / pkill / reopen as recovery
