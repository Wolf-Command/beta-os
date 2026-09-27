# GROK PLAN — WOLF AMG / ATRIUM NAV (Wave 5)
**Date:** 2026-09-22 ~17:30 WITA  
**Status:** THIN PLAN · **NEXT** after Wave-4 GGV DONE PASS  
**Priority:** HIGH · Global Nav migration order Wave **5**

## Lane
- Beta `/Users/wolfterminal/beta-os` · `:8788` only  
- machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
- Production `:8787` sacred — do not touch (pid currently 15975)  
- Preserve shared dirty `serve_beta` WIP — surgical only; commit deferred (head may stay `f3ab8f7`)

## Authority
- `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md`
- `docs/deliveries/GROK-PLAN-WOLF-NAV-MIGRATION-ORDER-2026-09-22.md` Wave **5**
- `docs/deliveries/GROK-SPEC-WOLF-TARGET-IA-2026-09-22.md` (Atrium/AMG › Inventory · Sales · Legal scoped · Coral ops Today)
- `docs/deliveries/GROK-SPEC-WOLF-ROLE-NAV-MATRIX-2026-09-22.md` (Coral landing Atrium/AMG Today/Operations; Amanda may have authorised Atrium sibling pages)
- `docs/deliveries/GROK-SPEC-WOLF-RESPONSIVE-HIERARCHY-CLEARANCE-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md`
- Prior: `GROK-REVIEW-WOLF-GGV-NAV-2026-09-22.md` (Wave 4 PASS=134)

## Scope (AMG / ATRIUM ONLY)
1. Soft-land **AMG / Atrium Overview** under BUSINESSES using existing Beta hrefs (`/amg-ops-pack` and existing atrium/amg cluster pages) — **no new dashboard HTML** unless a pure alias is strictly required.
2. **Coral landing = Atrium/AMG Today / Operations** via whoami — visibility-only; API auth canonical; Hidden≠permission. Prefer `/amg-ops-pack` or existing Coral Today surface already in Beta.
3. Breadcrumbs hierarchy: `WOLF › Atrium Management › AMG › …` (or current entity label already in tree) + parent UP on AMG surfaces; reuse `#wolfnav-crumbs` / `ROUTE_CRUMBS` — do not invent second chrome.
4. Grammar subnav labels stable (Overview · Operations · People · Customers · Finance · Standards · Issues · Intelligence) as **empty-honest** stubs where pages already exist; do not fake % or invent PROVEN. Finance stays **nested/visible-only** for Coral — no Zayen money execution.
5. Amanda: keep GGV landing (Wave4); authorised Atrium sibling pages may show per matrix — do not expand Amanda into full AMG ops.
6. Prove: Coral whoami landing AMG/Today; Progress/Empire/GGV depth/BZG Uma depth hidden per matrix for Coral; Matt reaches AMG; Amanda still lands GGV (Wave4 regression); Devi still lands Uma (Wave3 regression); anon 403 unchanged; one `#wolfnav`; `:8787` untouched.
7. Tests: add `scripts/tests/test_wolf_amg_nav.py` (and soft-assert prior Wave1–4 suites still green). Report PASS/FAIL.
8. Claim `bf-wolf-amg-nav-20260922`. Bound beta. Honesty `proven=false` `ready=false`.

## Out of scope
- Money / Zayen finance / payment approve / bank / tax.
- Client-private workspaces.
- Intel / System waves.
- Permissions catalog commissioning (separate CR).
- Screenshot V1 READY pack (debt stays on responsive CR).
- Invent PROVEN/READY / SYSTEM%.
- WIP quartet wipe; `git add .`; Production `:8787`.
- Parked FIN / HR / Trading / Devi retest branches.

## Prove
- Coral (fixture) landing AMG Today/Ops; Progress href absent; Empire/GGV-depth/Uma-depth absent from Coral bake.
- Breadcrumbs present on AMG Overview + at least one AMG child when authorised.
- UP from AMG child → AMG parent; HOME Coral → AMG Today/Ops.
- Live anon `:8788` AMG pages + pack APIs stay 403.
- Wave4 Amanda still GGV; Wave3 Devi still Uma Today (regressions).
- Suite PASS/FAIL count; claim honesty flags ready=false proven=false.

## Activation
- After Wave-4 DONE; create ACTIVE via `bf_write_run.py --activate`.
