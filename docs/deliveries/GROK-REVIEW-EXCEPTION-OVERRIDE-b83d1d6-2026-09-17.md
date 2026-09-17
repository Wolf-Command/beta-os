# GROK REVIEW — Exception / Override Governance `b83d1d6`

**Date:** 2026-09-17 WITA  
**Commit:** `b83d1d6` `feat(core): add governed exception control`  
**Parent:** `1d7fdff`  
**Plan:** `docs/deliveries/GROK-PLAN-EXCEPTION-OVERRIDE-2026-09-17.md`

## VERDICT: PASS

No material findings. Cursor fix loop NOT REQUIRED.

## Evidence

- Peaches re-run `test_exception_override.py`: **pass=88 fail=0**
- Cursor reported APR/DLG/Dual/Policy/SoD/Evidence regressions green
- Diff touches: exceptions.py, approvals/SoD wiring, migration 019, tests

### Diff stat
```
commit b83d1d67611da655c565a299d3569cf759c9024b
Author: Peaches (Beta baseline) <peaches@wolfcommand.local>
Date:   Thu Sep 17 13:47:15 2026 +0800

    feat(core): add governed exception control
    
    Co-authored-by: Cursor <cursoragent@cursor.com>

 docs/canon/EXCEPTION-OVERRIDE.md                   |   15 +
 ...CURSOR-MISSION-EXCEPTION-OVERRIDE-2026-09-17.md |   43 +
 .../GROK-PLAN-EXCEPTION-OVERRIDE-2026-09-17.md     |   74 ++
 scripts/core/approvals.py                          |  143 ++-
 scripts/core/audit.py                              |    8 +
 scripts/core/evidence.py                           |    1 +
 scripts/core/exceptions.py                         | 1067 ++++++++++++++++++++
 scripts/core/sod.py                                |    2 +-
 scripts/migrations/019_exception_override.sql      |   77 ++
 scripts/migrations/migrate_exception_override.py   |  330 ++++++
 scripts/tests/test_exception_override.py           |  868 ++++++++++++++++
 state/build-claims/2026-09-17.json                 |   14 +
 ...xception-override-backup-20260917-134639.sha256 |    1 +
 13 files changed, 2614 insertions(+), 29 deletions(-)

```

### Spot checks
- PERS-MATT gate: True
- client flags ignored: True
- consume: True
- authorise: True
- ALLOWED_UNDER_EXCEPTION: True
- exceptions import: True

## Red-team (actual behaviour via tests + code)

| Attack | Result |
|--------|--------|
| Generic force/override client flags | Ignored; REQUESTED ≠ usable |
| Non-Matt / forged authorise | Denied |
| Delegation claims for authorise | Ignored / blocked |
| Cross-object / wrong constraint | No match |
| Evidence exception covering SoD | Blocked |
| NON_EXCEPTIONABLE / missing registry | not_exceptionable |
| Single-use double consume | Second denied |
| Normal DENY rewritten PASS | PRESERVED (ALLOWED_UNDER_EXCEPTION + normal DENY codes) |
| Hard delete | Trigger refused |
| Live seed | exceptions=0 |

## Live counts

- auth = 0
- pol = 0
- sod = 0
- evr = 0
- exc = 0

## Backup

`/Users/wolfterminal/beta-os/catalog/backups/pre-exception-override-20260917-134639.sqlite`  
SHA-256: `2303e20bdfb45fca52d9ca9a828600d4cd150f71b12ab6c1d96fe77559648eb7`

## Design notes (non-blocking)

- Matt Person gate is base-case termination (no recursive exception-to-authorise-exception).
- EXCEPTION ≠ COMPLIANCE preserved via ALLOWED_UNDER_EXCEPTION + preserved normal deny codes.
- No operational exception seeded by this build.

## Production

NONE.
