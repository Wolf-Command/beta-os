# GROK PLAN — WOLF SHELL + TOKENS (Wave 1)
**Date:** 2026-09-22 ~15:53 WITA  
**Status:** DONE PASS — Peaches verify PASS=94 FAIL=0; review GROK-REVIEW-WOLF-SHELL-TOKENS-2026-09-22.md  
**Priority:** HIGH · standing gate after CORE close · `forbid_new_dashboard_surfaces` until this pack

## Lane
- Beta `/Users/wolfterminal/beta-os` · `:8788` only  
- machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
- Production `:8787` sacred — do not touch  
- Preserve shared dirty `serve_beta` WIP — surgical only; commit deferred if dirty (head may stay `f3ab8f7`)

## Authority (cite in Cursor mission)
- `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-GLOBAL-SHELL-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-DESIGN-SYSTEM-MAP-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-TARGET-IA-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-PAGE-TYPES-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-ROLE-NAV-MATRIX-2026-09-22.md`
- Order context: `GROK-PLAN-WOLF-NAV-MIGRATION-ORDER-2026-09-22.md` Wave **1**

## Scope (shell + tokens ONLY)
1. Extract `wolf-tokens.css` from existing `style.css` + sidenav CSS — **no** per-page restyle.
2. Evolve `sidenav.js` / `#wolfnav` toward IA sections **HOME / BUSINESSES / INTELLIGENCE / SYSTEM** with **same hrefs** (no broken links).
3. Optional non-breaking `data-wolf-page-type` / org attrs.
4. **Never** a second Boards menu.
5. No BU business logic, no API rewrites, no factory kill, no new dashboard surfaces.

## Prove
- One `#wolfnav` on ≥3 sample pages (Empire if present, Uma, Progress).
- Phone toggle preserved (`#wolfnav-t`).
- whoami filter still hides unauthorized hrefs.
- Anon/staff/owner smoke: no parallel nav; `:8787` untouched.
- Do **not** invent PROVEN/READY in UI copy.

## Out of scope
- Route merge/retire (later wave; needs Mac inventory of `mgmt-cluster` / `operator-depth`).
- Permissions commissioning packs.
- Any new dashboard HTML surfaces.

## Activation rule
- Create ACTIVE via `bf_write_run.py` **only after** P9 CORE ACTIVE is cleared.
- 