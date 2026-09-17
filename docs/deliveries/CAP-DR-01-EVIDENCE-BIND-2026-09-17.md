# CAP-DR-01 — EVIDENCE BIND PACK (OVERNIGHT P1)

> **OWNER AUDIT 2026-09-18 — Matt REJECTED PROVEN.**  
> Remains **SPECIFIED**. The 29 Aug B2 restore drill is retained as historical evidence only; it is insufficient for PROVEN until a deterministic canonical restore-drill proof exists. See `docs/deliveries/EVIDENCE-REMEDIATION-DR01-INTG07-2026-09-18.md`.

**Date:** 2026-09-17
**CAP-ID:** CAP-DR-01 Backup / Restore Testing / Disaster Recovery
**Prior maturity:** SPECIFIED
**Proposed maturity (overnight):** PROVEN — **REJECTED 2026-09-18**
**Current maturity:** SPECIFIED
**Class:** PROVE WHAT EXISTS — no new backup/restore rewrite
**Production mutations:** NONE (read-only evidence bind)

## Locatable implementation

- `restore-drill.py` at `/Users/wolfterminal/.openclaw/workspace/wolf-system/scripts/restore-drill.py` exists (39018 bytes, mtime 2026-08-11T08:49:03.691526)
- Wrapper: `WolfCommandSystem/phase2/38-restore-drill.sh`
- Daily backup status: `~/.openclaw/state/backup_status.json`

## Current backup health (read-only snapshot)

- last_run: 2026-09-17T02:00:01
- local_ok: True · b2_ok: True · secrets_encrypted_ok: True
- local_size_bytes: 384333600 · files_count: 9616

## Deterministic restore proof (existing — historical)

- Bound report: `/Users/wolfterminal/WolfCommandSystem/WolfCommand/01-Wolf-Command/System-Registry/B2-RESTORE-DRILL-2026-08-29.md`
- Verdict (2026-08-29): B2 restorable YES; restored 337965245 bytes; sha256 match YES
- Method: rclone copyto temp + sha256 vs local original; temp deleted; nothing deleted on B2/R2/NAS
- Secrets contents NOT restored (names only / not drilled) — correct

## Why not PROVEN / READY

- Matt 2026-09-18: historical 29 Aug drill ≠ deterministic canonical CAP-bound restore-drill proof
- Automated CAP-bound Beta prove pack for restore-drill.py not yet wired into beta-os test suite
- READY deferred until a fresh CAP-bound drill log is attached under beta-os deliveries

## Red team

| Attack | Result |
| --- | --- |
| Backup write ≠ restore | PASS — sha256 restore match documented |
| Secrets leak in drill | PASS — secrets not written to disk in drill design |
| Practice-only claim | PASS — script + dated restore report bound |
| Auto-raise to READY on old drill | FAIL intentionally — withhold READY |
| Auto-raise to PROVEN on old drill | FAIL intentionally — owner rejected 2026-09-18 |

CLAIMED ≠ VERIFIED · DESIGNED ≠ BUILT ≠ TESTED ≠ LIVE
