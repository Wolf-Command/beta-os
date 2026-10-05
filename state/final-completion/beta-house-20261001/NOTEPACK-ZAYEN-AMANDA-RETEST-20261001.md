# NOTEPACK — Zayen / Amanda finance retest (post Owner ACCEPT)

`2026-10-01T11:24:15+08:00` · Peaches · **Do not ping staff** · Owner ACCEPT entity-isolation `2026-10-01T11:21:00+08:00`

## Context
Finding BREACH-2026-09-30-J1 **CLOSED_REPAIRED_VERIFIED**. Server-side 50/50 PASS.  
**KEEP ASG-ZAYEN-BZG-FC-1.** human_finance_commissioning still **false**.

## Zayen — SP-ZAYEN-AMG-BZG-FINANCE
| Entity | Expect |
|--------|--------|
| ENT-AMG | YES (FC / atrium) |
| ENT-BZG | YES (FC / AP — seat kept) |
| ENT-GGV | ZERO / DENY |

## Zayen — ZAYEN-CF-BROWSER-ENTITY-ISOLATION-UI (NEW)
- Class: **STAFF_COMMISSIONING**
- Method: authenticated CF Access browser session (not bare localhost matrix)
- Prove UI/session path: **AMG YES · BZG YES · GGV DENY**
- `matrix_pass=null` until human
- Does **NOT** reopen architecture finding unless browser exposes regression

## Amanda — SP-AMANDA-GGV-FINANCE
| Entity | Expect |
|--------|--------|
| ENT-GGV | YES (Operator) |
| ENT-AMG / ENT-BZG | NO |

## Routing
Needs-you / staff-ops-routing / MY COMMISSIONING only. **No agent Slack ping.**
