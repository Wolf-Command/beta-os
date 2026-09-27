# GROK PLAN — WOLF GGV NAV (Wave 4)
**Date:** 2026-09-22 ~17:18 WITA  
**Status:** THIN PLAN · **NEXT** after Wave-3 BZG+Uma DONE PASS  
**Priority:** HIGH · Global Nav migration order Wave **4**

## Lane
- Beta `/Users/wolfterminal/beta-os` · `:8788` only  
- machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
- Production `:8787` sacred — do not touch  
- Preserve shared dirty `serve_beta` WIP — surgical only; commit deferred (head may stay `f3ab8f7`)

## Authority
- `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md`
- `docs/deliveries/GROK-PLAN-WOLF-NAV-MIGRATION-ORDER-2026-09-22.md` Wave **4**
- `docs/deliveries/GROK-SPEC-WOLF-TARGET-IA-2026-09-22.md` (GGV › Habitat / Lead Spine)
- `docs/deliveries/GROK-SPEC-WOLF-ROLE-NAV-MATRIX-2026-09-22.md` (Amanda landing GGV)
- `docs/deliveries/GROK-SPEC-WOLF-RESPONSIVE-HIERARCHY-CLEARANCE-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md`
- Prior: `GROK-REVIEW-WOLF-BZG-UMA-NAV-2026-09-22.md` (Wave 3 PASS=111)

## Scope (GGV ONLY)
1. Soft-land **GGV Overview** under BUSINESSES using existing Beta hrefs (`/ggv-ops-pack`, habitat-operator, lead-spine surfaces) — **no new dashboard HTML** unless a pure alias is strictly required.
2. **Amanda landing = GGV Overview** (`/ggv-ops-pack` or current canonical) via whoami — visibility-only; API auth canonical; Hidden≠permission.
3. Breadcrumbs hierarchy: `WOLF › Goss Group › GGV › …` (and parent UP) on GGV/Habitat surfaces; reuse `#wolfnav-crumbs` / `ROUTE_CRUMBS` — do not invent second chrome.
4. Grammar subnav labels stable (Overview · Operations · People · Customers · Finance · Standards · Issues · Intelligence) as **empty-honest** stubs where pages already exist; do not fake % or invent PROVEN.
5. Client projection **not** in this wave (perms pack later) — keep client fail-closed / existing deny.
6. Prove: Amanda whoami landing GGV; Progress/Empire/BZG Uma depth/AMG still hidden per matrix; Matt still reaches GGV; Devi still lands Uma (Wave3 regression); anon 403 unchanged; one `#wolfnav`; `:8787` untouched.
7. Tests: add `test_wolf_ggv_nav.py` (and soft-assert prior Wave1–3 suites still green). Report PASS/FAIL.
8. Claim `bf-wolf-ggv-nav-20260922`. Bound beta.

## Out of scope
- Money / Zayen finance / payment approve / Habitat CRM cutover.
- Client-private workspaces commissioning.
- AMG / Intel / System waves.
- Permissions catalog commissioning (separate CR).
- Screenshot V1 READY pack (debt stays on responsive CR).
- Invent PROVEN/READY / SYSTEM%.
- WIP quartet wipe; `git add .`; Production.

## Prove
- Amanda (fixture) landing GGV Overview; Progress href absent; Empire absent from Amanda bake.
- Breadcrumbs present on GGV Overview + at least one Habitat/Lead path when authorised.
- UP from GGV child → GGV parent; HOME Amanda → GGV Overview.
- Live anon `:8788` GGV pages + pack APIs stay 403.
- Wave3 Devi landing still Uma Today (regression).
- Suite PASS/FAIL count; claim honesty flags ready=false proven=false.

## Activation
- After Wave-3 DONE; create ACTIVE via `bf_write_run.py --activate`.
