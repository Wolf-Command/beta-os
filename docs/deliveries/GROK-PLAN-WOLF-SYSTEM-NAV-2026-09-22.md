# GROK PLAN — WOLF SYSTEM NAV (Wave 7)
**Date:** 2026-09-22 ~18:05 WITA  
**Status:** THIN PLAN · **NEXT** after Wave-6 Intel DONE PASS  
**Priority:** HIGH · Global Nav migration order Wave **7**

## Lane
- Beta `/Users/wolfterminal/beta-os` · `:8788` only  
- machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
- Production `:8787` sacred — do not touch (pid currently 15975)  
- Preserve shared dirty `serve_beta` WIP — surgical only; commit deferred (head may stay `f3ab8f7`)

## Authority
- `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md`
- `docs/deliveries/GROK-PLAN-WOLF-NAV-MIGRATION-ORDER-2026-09-22.md` Wave **7**
- `docs/deliveries/GROK-SPEC-WOLF-TARGET-IA-2026-09-22.md` (SYSTEM Owner-only)
- `docs/deliveries/GROK-SPEC-WOLF-ROLE-NAV-MATRIX-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-RESPONSIVE-HIERARCHY-CLEARANCE-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md`
- Prior: `GROK-REVIEW-WOLF-INTEL-NAV-2026-09-22.md` (Wave 6 PASS=165)

## Scope (SYSTEM ONLY)
1. Soft-land **Owner-only SYSTEM** section using existing Progress / Integrations / Sale / Factory surfaces — **no new dashboard HTML** unless a pure alias is strictly required.
2. Staff (Haikal / Coral / Amanda / Devi) **hide SYSTEM** admin via nav; API auth canonical; Hidden≠permission.
3. Breadcrumbs hierarchy: `WOLF › System › …` (+ Progress / Integrations / Sale / Factory children when authorised) + parent UP; reuse `#wolfnav-crumbs` / `ROUTE_CRUMBS`.
4. Grammar / SYSTEM subnav labels honest EMPTY where missing — never fake %.
5. Prove: Owner/Matt reaches System/Progress; staff do not get SYSTEM admin via nav; Wave1–6 landings retained; anon 403 unchanged; one `#wolfnav`; `:8787` untouched.
6. Tests: add `scripts/tests/test_wolf_system_nav.py` (+ soft-assert prior Wave1–6 suites still green). Report PASS/FAIL.
7. Claim `bf-wolf-system-nav-20260922`. Bound beta. Honesty `proven=false` `ready=false`.

## Out of scope
- Money / Zayen / payment / bank / tax.
- Devi retest / F&B commissioning.
- Invent PROVEN/READY / SYSTEM% / CAP-CORE-11 promotion.
- New dashboard sprawl; WIP quartet wipe; `git add .`; Production `:8787`.
- Wave 8 specialist remaining; permissions catalog commissioning (separate CR).
- Screenshot V1 READY pack (debt stays on responsive CR).
- Parked FIN / HR / Trading branches.

## Prove
- Owner whoami can reach Progress (and System section children as built); crumbs `WOLF › System › …`.
- Haikal / Coral / Amanda / Devi do **not** gain SYSTEM admin via nav alone; API still fail-closed.
- Soft regressions Wave1–6 green (Intel PASS=165 / AMG 147 / GGV 134 / BZG 111).
- Live anon `:8788` system/progress pages + pack APIs stay 403.
- Suite PASS/FAIL; honesty ready=false proven=false.

## Activation
- After Wave-6 DONE; create ACTIVE via `bf_write_run.py --activate`.
