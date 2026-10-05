# SECURITY FAIL — Soft bleed Zayen ↔ GGV Finance — CLOSED

**As of:** 2026-10-01T11:23:30+08:00  
**Finding ID:** BREACH-2026-09-30-J1-ZAYEN-GGV-NOTA-READ  
**Severity (historical):** FAIL / RED (architecture defect as originally recorded)  
**Status:** **CLOSED_REPAIRED_VERIFIED**  
**staff_ready:** false · **human_commissioned:** false

## Closure (Owner ACCEPT)

| Field | Value |
|-------|-------|
| owner_accept_wita | 2026-10-01T11:21:00+08:00 |
| verdict | **REPAIRED + VERIFIED** |
| basis | 50/50 server-side prove |
| human_finance_commissioning | **false** (do NOT treat as Finance human commissioning complete) |

Owner ACCEPT of entity-isolation repair. Residual authenticated Zayen CF/browser UI prove (**AMG YES · BZG YES · GGV DENY**) remains in **STAFF_COMMISSIONING** queue — does **not** reopen architecture finding unless browser test exposes regression.

## Owner disposition (unchanged / canonical)

Rejected LEAVE / REVOKE / STRIP. **KEEP** `ASG-ZAYEN-BZG-FC-1`.  
Intentional: Zayen AMG FC YES · BZG FC YES · GGV Finance ZERO.

## Defect class (historical)

Vacuous bare-target ALLOW + scope-blind `staff_home` finance codes. Repaired via `entity_scope_required` + `finance_*_by_entity` (see ENTITY-ISOLATION-REPAIR-20261001).

## Citations

- OWNER-ACCEPT-ENTITY-ISOLATION-20261001
- ENTITY-ISOLATION-REPAIR-20261001 (50/50 PASS)
- Vesper GRILL-BREACH-2026-10-01-J1-QUIET-PROBE + 2026-09-30 J1
- Breach FINDINGS-LATEST + findings/2026-10-01-j1-quiet-probe-red-zayen-ggv-nota-read.md

## Sacred

Prod :8787 pid **15975** READ-ONLY · Beta :8788 pid **12379** · Finance :8790 pid **45751** SoD unchanged.
