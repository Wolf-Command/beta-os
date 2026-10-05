# ENTITY-ISOLATION-REPAIR-20261001

**As of:** 2026-10-01T11:23:30+08:00  
**Order:** P0 OWNER ORDER 1 Oct 2026 ~09:36 WITA · **Owner ACCEPT** 2026-10-01T11:21:00+08:00  
**Finding:** BREACH-2026-09-30-J1-ZAYEN-GGV-NOTA-READ → **CLOSED_REPAIRED_VERIFIED**  
**Status:** **REPAIRED_VERIFIED_OWNER_ACCEPTED**  
**staff_ready:** false · **human_commissioned:** false · **Exit Report:** NOT_CREATED

## Owner ACCEPT

Verdict **REPAIRED + VERIFIED** on 50/50 server-side prove.  
**Not** Finance human commissioning complete. Residual CF/browser UI → **STAFF_COMMISSIONING** (`ZAYEN-CF-BROWSER-ENTITY-ISOLATION-UI`), not architecture OPEN.

## Intentional seating (canonical)

KEEP `ASG-ZAYEN-BZG-FC-1`. Zayen AMG FC YES · BZG FC YES · GGV Finance ZERO.

## Before → After (unchanged from repair)

| Check | Before | After |
|-------|--------|-------|
| Zayen bare `finance.nota.read` | ALLOW | **DENY** `entity_scope_required` |
| Zayen ENT-GGV | DENY | DENY |
| Zayen ENT-BZG | ALLOW | ALLOW (seat kept) |
| Prove matrix | — | **50/50 PASS** |

## Residual (STAFF_COMMISSIONING)

Authenticated Zayen CF/browser session: prove AMG YES / BZG YES / GGV DENY. Does **not** reopen architecture finding unless regression.

## Sacred pids (current)

Prod :8787 **15975** untouched · Beta :8788 **12379** · Finance :8790 **45751** SoD unchanged.
