# GROK PLAN — WOLF EMPIRE HOME (Wave 2)
**Date:** 2026-09-22 ~16:25 WITA  
**Status:** THIN PLAN · **NEXT** after Wave-1 shell+tokens DONE PASS  
**Priority:** HIGH · Global Nav migration order Wave **2**

## Lane
- Beta `/Users/wolfterminal/beta-os` · `:8788` only  
- machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
- Production `:8787` sacred — do not touch  
- Preserve shared dirty `serve_beta` WIP — surgical only; commit deferred (head may stay `f3ab8f7`)

## Authority
- `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md`
- `docs/deliveries/GROK-PLAN-WOLF-NAV-MIGRATION-ORDER-2026-09-22.md` Wave **2**
- `docs/deliveries/GROK-SPEC-WOLF-GLOBAL-SHELL-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-TARGET-IA-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-ROLE-NAV-MATRIX-2026-09-22.md`
- `docs/deliveries/GROK-SPEC-WOLF-PERMISSIONS-AUDIENCE-2026-09-22.md`
- Prior: `GROK-REVIEW-WOLF-SHELL-TOKENS-2026-09-22.md` (Wave 1 PASS=94)

## Scope (Owner / Empire HOME ONLY)
1. Make **Owner landing = Empire** (`/owner-empire-pack` and/or clean `/wolf` alias → Empire) using existing Wave-1 `#wolfnav` chrome — do not invent a second nav.
2. Soft-land **Needs You** stub under HOME (existing `/staff-ops-routing` href OK; deepen only if already present — no new sprawl page unless alias).
3. Priorities / radar: absorb later stub OK — do **not** mass-retire `radar.html` this pack (Wave route-merge later).
4. Staff still blocked from Progress / SYSTEM; whoami filter remains visibility-only; API auth canonical; Hidden≠permission.
5. Optional: Empire body uses `data-wolf-page-type="DASHBOARD"` already — extend breadcrumbs/org context non-breaking if cheap.
6. Prove Owner path lands Empire with one `#wolfnav`; Devi/staff cannot open Progress via nav; anon 403 unchanged; `:8787` untouched.

## Out of scope
- Route merge/retire of mgmt-cluster / operator-depth (later wave + Mac inventory).
- BZG/Uma / GGV / AMG content migration (Waves 3–5).
- Permissions catalog commissioning (separate CR).
- Finance/HR/Trading; money; CF Access; Production.
- Invent PROVEN/READY / SYSTEM%.
- New dashboard HTML surfaces beyond HOME alias if strictly required.

## Prove
- Owner (Matt) whoami: HOME Empire primary; Progress still under SYSTEM.
- Staff/Devi: Progress href hidden; Empire hidden if out of scope.
- Live `:8788` Empire (auth) has single `#wolfnav` + `#wolfnav-t`.
- Anon Empire/Progress APIs stay 403 where already gated.
- Tests: extend or add `test_wolf_empire_home.py` (or shell suite addendum) — report PASS/FAIL.
- Claim `bf-wolf-empire-home-20260922`. Bound beta.

## Activation
- After Wave-1 DONE; create ACTIVE via `bf_write_run.py --activate`.
