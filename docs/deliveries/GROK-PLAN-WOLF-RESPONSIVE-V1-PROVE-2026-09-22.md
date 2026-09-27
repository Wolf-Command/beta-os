# GROK PLAN — Wolf Responsive + Hierarchy + Clearance V1 Prove — 2026-09-22

**Status:** THIN PLAN · **NEXT** after Wave-8 Specialist DONE PASS=232  
**Run:** `BF-wolf-responsive-v1-prove-20260922`  
**Claim:** `bf-wolf-responsive-v1-prove-20260922`  
**Bound:** beta `:8788` only · Production `:8787` sacred  
**CR:** `wolf-global-nav-responsive-hierarchical-20260922` / `e4bee2462ff81803287fa3562776d8ec` (stay OPEN unless V1 READY bars met — do not invent READY)

## Authority
- `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-RESPONSIVE-HIERARCHY-CLEARANCE-2026-09-22.md`
- `docs/deliveries/OWNER-CORRECTION-NAV-RESPONSIVE-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-ROLE-NAV-MATRIX-2026-09-22.md`
- Prior: Wave8 Specialist `GROK-REVIEW-WOLF-SPECIALIST-NAV-2026-09-22.md` PASS=232

## Scope (V1 PROVE PACK — engineering + automated proof; screenshots when feasible)
Close Owner correction debt that blocks Global Nav V1 READY notify. Prove, do not invent:

1. **Responsive shell** — one shell adapts desktop/tablet/mobile; tables→cards on mobile; no tiny desktop controls; tokens/media already seeded in Wave2 — extend prove across Empire / BZG Uma / GGV / AMG / Intel / System sample pages.
2. **Direction** — UP / BACK / FORWARD-NEXT (when authorised) / HOME on primary page types; no browser-back dependence.
3. **Breadcrumbs** — hierarchy-aware on object/detail samples (Empire→BU→site→workspace→object).
4. **Clearance-aware nav** — Person→Role→Assignment→Scope→Permission→Audience; prove Matt/Owner, Devi F&B, Haikal content, Client projection, unauth. Hidden ≠ permission; typed URL/API fail closed.
5. **Context switcher** — only multi-assignment identities; never unauthorised contexts.
6. **Role matrix + deny matrix** — expand automated deny for Progress/API/Integrations/Sale + key BU routes; keep soft Wave1–8 green.
7. **Screenshots** — if Mac can capture without new deps: desktop + mobile viewport captures under `docs/deliveries/evidence/wolf-rhc-v1-20260922/` for Empire + one BU + one System surface. If blocked, register DEBT explicitly; still ship automated bars.
8. Tests: `scripts/tests/test_wolf_responsive_v1_prove.py` (+ soft priors Wave1–8). Claim honesty `proven=false` `ready=false` unless ALL GATES `v1_ready_requires` met with evidence files.

## Out of scope
- Production `:8787` · money/Zayen/bank/tax · Trading execution · CF seats/tokens  
- Devi retest / F&B commissioning · invent PROVEN/READY / CAP promotions  
- New dashboard sprawl · WIP quartet wipe · `git add .` · reopen parked FIN/HR/Trading  
- Permissions catalog full commissioning (separate) · client buyer-mode expansion beyond projection proof

## Prove bars (GATES v1_ready_requires)
| Bar | Need |
|-----|------|
| desktop_screenshots | evidence files OR explicit DEBT |
| mobile_screenshots | evidence files OR explicit DEBT |
| role_matrix_proof | automated tests Matt/Devi/Haikal/client/unauth |
| url_api_denial_proof | typed URL + API 403 matrix |
| breadcrumb_back_up_proof | automated +/or screenshot |
| context_switch_proof | multi-assignment only |

**READY notify only if all six have real evidence.** Otherwise PASS engineering with CR stays OPEN and DEBT listed.

## Lane
- Beta `/Users/wolfterminal/beta-os` · `:8788`  
- machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
- Preserve dirty `serve_beta` WIP — surgical only; head may stay `f3ab8f7`  
- Prod pid currently 15975 untouched

## Activation
Create ACTIVE via `bf_write_run.py --activate`. EXIT: SUCCESS or EXIT: FAILED.
