# CURSOR PACK — BZG-CLOSE-GOVERNED-TAKEOVER-1 (P0 OWNER TAKEOVER)

**Owner drain** · local beta-os · parent tip `69de1bb` · **NO push** · prod `:8787` READ-ONLY

## Problem
Deployed `/uma-blu-close` shows: "This close is already taken by another authorised closer."
Pull ESB / Take Photo / Upload Photo disabled. Concurrency lock is correct — **no governed takeover UI/API**.

## Non-negotiables
- Do **NOT** delete the existing close
- Do **NOT** clear ownership directly in the database
- Do **NOT** weaken concurrency control
- Ordinary cashiers must **NOT** steal another closer's active close
- Preserve all work: photos, extracts, confirmed values, cash, EDC, QRIS, notes, exceptions, evidence
- Full audit: original closer, takeover actor, reason, timestamp, state before/after
- `staff_ready=false` · Iza commissioning remains **FAIL** even if Matt finishes tonight

## Implement (reusable BZG engine — Role/Scope/Permission)
1. Trace who holds tonight's Uma close (likely Iza) via venue_daily_closes / take_open_venue_close lock.
2. Add permission e.g. `venue.close.reassign` / takeover for Captain/manager/supervisor/Owner (RBAC + scope) — **not** ordinary cashier.
3. API: view current holder; **Reassign Close** and/or **Take Over Close** requiring non-empty **reason**.
4. UI on `dashboards/uma-blu-close.html`: when locked by another authorised closer, authorised supervisor sees holder name + Take Over / Reassign + reason field. After success, controls enable for new closer; show prior entered work.
5. Audit event recording original closer, actor, reason, before/after state; keep history.
6. Restart Beta `:8788`; prove deployed route (not repo-only).
7. Tests: cashier cannot takeover; authorised can with reason; work preserved; audit present; concurrency still blocks peer cashiers.

## Exit
RESULT under `state/bzg-daily-close/` + `state/iza-uma/`. EXIT:0 tip SHA.
Do **not** tell Matt ready — Peaches verifies then **MATT RETEST READY**.
