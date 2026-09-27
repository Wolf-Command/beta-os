# GROK PLAN — WOLF INTELLIGENCE NAV (Wave 6)
**Date:** 2026-09-22 ~17:47 WITA  
**Status:** THIN PLAN · **NEXT** after Wave-5 AMG DONE PASS  
**Priority:** HIGH · Global Nav migration order Wave **6**

## Lane
- Beta `/Users/wolfterminal/beta-os` · `:8788` only  
- machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
- Production `:8787` sacred — do not touch (pid currently 15975)  
- Preserve shared dirty `serve_beta` WIP — surgical only; commit deferred (head may stay `f3ab8f7`)

## Authority
- `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md`
- `docs/deliveries/GROK-PLAN-WOLF-NAV-MIGRATION-ORDER-2026-09-22.md` Wave **6**
- `docs/deliveries/GROK-SPEC-WOLF-TARGET-IA-2026-09-22.md` (Intelligence Home inherits requester permissions)
- `docs/deliveries/GROK-SPEC-WOLF-ROLE-NAV-MATRIX-2026-09-22.md` (Haikal/Content → content workspace under Intelligence→Content; Owner Intel admin)
- `docs/deliveries/GROK-SPEC-WOLF-RESPONSIVE-HIERARCHY-CLEARANCE-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md`
- Prior: `GROK-REVIEW-WOLF-AMG-NAV-2026-09-22.md` (Wave 5 PASS=147)

## Scope (INTELLIGENCE ONLY)
1. Soft-land **Intelligence Home** under INTEL section using existing `/intel-ops-pack` (+ `/intel-mgmt-cluster` if already linked) — **no new dashboard HTML** unless a pure alias is strictly required.
2. **Content home decision:** put Content workspace (`/content-2.0` or current content hub href) under Intelligence→Content for SPECIALIST_CONTENT (Haikal) landings — authorised brands only; do not open Owner Intelligence admin to content crew; no side door past API auth.
3. Breadcrumbs hierarchy: `WOLF › Intelligence › …` (+ Content child when authorised) + parent UP; reuse `#wolfnav-crumbs` / `ROUTE_CRUMBS` — do not invent second chrome.
4. Grammar / INTEL subnav labels honest EMPTY where missing — never fake %. Intel inherits requester perms (Hidden≠permission; API auth canonical).
5. Prove: Owner/Matt reaches Intel Home; Haikal lands Content (or authorised Intel→Content); Coral/Amanda/Devi do **not** gain Intel admin side door; Wave3–5 landings retained; anon 403 unchanged; one `#wolfnav`; `:8787` untouched.
6. Tests: add `scripts/tests/test_wolf_intel_nav.py` (+ soft-assert prior Wave1–5 suites still green). Report PASS/FAIL.
7. Claim `bf-wolf-intel-nav-20260922`. Bound beta. Honesty `proven=false` `ready=false`.

## Out of scope
- Money / Zayen / payment / bank / tax.
- Client-private workspaces / buyer mode expansion.
- System / Progress / Sale / Factory wave (Wave 7).
- Permissions catalog commissioning (separate CR).
- Screenshot V1 READY pack (debt stays on responsive CR).
- Invent PROVEN/READY / SYSTEM% / auto-promote learning rules.
- WIP quartet wipe; `git add .`; Production `:8787`.
- Parked FIN / HR / Trading / Devi retest branches.

## Prove
- Owner whoami can reach `/intel-ops-pack`; crumbs `WOLF › Intelligence`.
- Haikal/content landing Content under Intel→Content (or documented decision if content stays GGV-scoped with Intel link only — pick one, prove it).
- Coral/Amanda/Devi cannot open Owner Intel admin via nav alone; API still fail-closed.
- Soft regressions Wave1–5 green.
- Live anon `:8788` intel pages + pack APIs stay 403.
- Suite PASS/FAIL; honesty ready=false proven=false.

## Activation
- After Wave-5 DONE; create ACTIVE via `bf_write_run.py --activate`.
