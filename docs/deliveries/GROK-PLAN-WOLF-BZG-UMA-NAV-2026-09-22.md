# GROK PLAN — WOLF BZG + UMA NAV (Wave 3)
**Date:** 2026-09-22 ~17:00 WITA  
**Status:** THIN PLAN · **NEXT** after Wave-2 Empire HOME + RHC FIX DONE PASS  
**Priority:** HIGH · Global Nav migration order Wave **3**

## Lane
- Beta `/Users/wolfterminal/beta-os` · `:8788` only  
- machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
- Production `:8787` sacred — do not touch  
- Preserve shared dirty `serve_beta` WIP — surgical only; commit deferred (head may stay `f3ab8f7`)

## Authority
- `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md`
- `docs/deliveries/GROK-PLAN-WOLF-NAV-MIGRATION-ORDER-2026-09-22.md` Wave **3**
- `docs/deliveries/GROK-SPEC-WOLF-TARGET-IA-2026-09-22.md` (BZG › Uma Blu › Today)
- `docs/deliveries/GROK-SPEC-WOLF-ROLE-NAV-MATRIX-2026-09-22.md` (Devi landing)
- `docs/deliveries/GROK-SPEC-WOLF-RESPONSIVE-HIERARCHY-CLEARANCE-2026-09-22.md`
- Prior: `GROK-REVIEW-WOLF-EMPIRE-HOME-2026-09-22.md` (Wave 2 + FIX PASS=174)

## Scope (BZG + Uma ONLY)
1. Soft-land **BZG Overview** entry under BUSINESSES using existing Beta hrefs (prefer existing Uma/BZG routes — **no new dashboard HTML** unless a pure alias page is strictly required).
2. **Devi landing = Uma Blu Today** (`/bzg/uma-blu` or current canonical Today) via whoami — visibility-only; API auth canonical; Hidden≠permission.
3. Breadcrumbs hierarchy: `WOLF › Blu Zone › Uma Blu › Today` (and parent UP) on Uma/BZG surfaces; reuse `#wolfnav-crumbs` / `ROUTE_CRUMBS` — do not invent second chrome.
4. Grammar subnav labels stable (Overview · Operations · Issues · …) as **empty-honest** stubs where pages already exist; do not fake % or invent PROVEN.
5. Legacy `/bzg-uma-blu*` / old uma paths: safe redirect or alias into canonical shell route when cheap.
6. Prove: Devi whoami landing Today; Progress/Empire/GGV/AMG still hidden; Matt still reaches BZG; anon 403 unchanged; one `#wolfnav`; `:8787` untouched.
7. Tests: extend `test_wolf_empire_home.py` or add `test_wolf_bzg_uma_nav.py` — report PASS/FAIL.
8. Claim `bf-wolf-bzg-uma-nav-20260922`. Bound beta.

## Out of scope
- Money / petty-cash execution / Zayen finance / payment approve.
- New mgmt-cluster promotion into primary nav.
- GGV / AMG / Intel / System waves.
- Permissions catalog commissioning (separate CR).
- Screenshot V1 READY pack (debt stays on responsive CR).
- Invent PROVEN/READY / SYSTEM%.
- WIP quartet wipe; `git add .`; Production.

## Prove
- Devi (fixture) landing Today; Progress href absent; Empire absent.
- Breadcrumbs present on Uma Today + at least one BZG parent path.
- UP from Today → Uma/BZG parent; HOME → Devi landing.
- Live anon `:8788` Uma/BZG pages + pack APIs stay 403.
- Suite PASS/FAIL count; claim honesty flags ready=false proven=false.

## Activation
- After Wave-2 DONE; create ACTIVE via `bf_write_run.py --activate`.
