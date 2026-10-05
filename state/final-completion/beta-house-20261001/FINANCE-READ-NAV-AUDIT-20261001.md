# FINANCE-READ-NAV-AUDIT — 1 Oct 2026 WITA

Generated: `2026-10-01T09:53:00+08:00` · Peaches-executor · Prod :8787 untouched

## Result
**No chrome/nav consumer of bare boolean `finance_read`.** Nav uses `wolf_shell.authority_nav_from_assignments` (ROLE+SCOPE). Zayen nav proves AMG+BZG only; GGV finance absent.

## Producer
`staff_home.authority.finance_read = any(finance_read_by_entity.values())` — OR-compat kept.
Prefer `finance_read_by_entity` for any new chrome.

## Surgical apply
Semantics stamp on authority dict (no permission change). Seats kept · ASG-ZAYEN-BZG-FC-1 kept · Finance SoD unchanged.

## Residual
CF JWT browser as zayen@ `/ggv/finance` NOT_PROVED this tick. staff_ready=false · desktop_gate_ready=false.
