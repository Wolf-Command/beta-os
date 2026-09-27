# GROK PLAN — WOLF SPECIALIST NAV (Wave 8)
**Date:** 2026-09-22 18:26 WITA  
**Status:** THIN PLAN · **NEXT** after Wave-7 System DONE PASS=197  
**Priority:** HIGH · Global Nav migration order Wave **8**

## Lane
- Beta `/Users/wolfterminal/beta-os` · `:8788` only  
- machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
- Production `:8787` sacred — do not touch (pid currently 15975)  
- Preserve shared dirty `serve_beta` WIP — surgical only; commit deferred (head may stay `f3ab8f7`)

## Authority
- `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md`
- `docs/deliveries/GROK-PLAN-WOLF-NAV-MIGRATION-ORDER-2026-09-22.md` Wave **8**
- `docs/deliveries/GROK-SPEC-WOLF-TARGET-IA-2026-09-22.md` (Hidden specialist boards)
- `docs/deliveries/GROK-SPEC-WOLF-ROLE-NAV-MATRIX-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-RESPONSIVE-HIERARCHY-CLEARANCE-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md`
- Prior: `GROK-REVIEW-WOLF-SYSTEM-NAV-2026-09-22.md` (Wave 7 PASS=197)

## Scope (SPECIALIST REMOVAL ONLY)
1. Ensure trading / travel / spartacus / other legacy specialist boards are **not primary** in `#wolfnav` IA (HOME/BUSINESSES/INTEL/SYSTEM). Hidden ≠ deleted — reachable via drill, search (RBAC), or bookmark **only if API allows**.
2. Soft redirects OK for old specialist entry points that used to sit in primary chrome — do not invent new sprawl pages.
3. Preserve Wave1–7 soft regressions (System/Intel/AMG/GGV/BZG/Empire/Shell landings + Owner SYSTEM hide for staff).
4. Breadcrumbs / UP / HOME grammar unchanged for remaining primary surfaces.
5. Tests: add `scripts/tests/test_wolf_specialist_nav.py` (+ soft prior Wave1–7). Prove: specialist not in primary Owner nav sections; staff matrices unchanged; anon 403 unchanged; one `#wolfnav`; `:8787` untouched.
6. Claim `bf-wolf-specialist-nav-20260922`. Bound beta. Honesty `proven=false` `ready=false`.

## Out of scope
- Money / Zayen / payment / bank / tax / Trading execution (Flint reserved — never trade).
- Devi retest / F&B commissioning.
- Invent PROVEN/READY / CAP promotions.
- New dashboard sprawl; WIP quartet wipe; `git add .`; Production `:8787`.
- Full responsive screenshot V1 READY pack (debt stays on responsive CR — may follow as next pack after Wave8).
- Parked FIN / HR / Trading branches; permissions catalog commissioning.

## Prove
- Owner whoami primary nav has no trading/travel/spartacus as top-level IA items.
- Soft regressions Wave1–7 green (System PASS=197 prior).
- Live anon `:8788` progress/integration/sale stay 403.
- Suite PASS/FAIL; honesty ready=false proven=false.

## Activation
- After Wave-7 DONE; create ACTIVE via `bf_write_run.py --activate`.
