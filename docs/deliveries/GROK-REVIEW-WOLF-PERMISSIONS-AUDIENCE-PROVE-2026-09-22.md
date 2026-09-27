# GROK REVIEW — Wolf Permissions / Audience Prove — 2026-09-22

**Run:** `BF-wolf-permissions-audience-prove-v2-20260922` (FIX1 recover after prior banner-only death)  
**Peaches decision:** PASS (suite PASS=193; soft Wave8 PASS=232 incl Wave1–7; live anon 403 on Progress/Integrations/Sale + APIs; four layers on Empire+Uma+Progress; role matrix Matt/Devi/Haikal/client/unauth; honesty proven=false ready=false; :8787 pid 15975 untouched)  
**Head:** `f3ab8f7` deferred · Production `:8787` not mutated (pid **15975** unchanged)  
**Claim:** `bf-wolf-permissions-audience-prove-20260922` · bound beta · proven=false · ready=false  
**Prior:** RHC V1 Prove PASS=248 · Wave8 Specialist PASS=232

## Evidence

| Check | Result |
|-------|--------|
| `test_wolf_permissions_audience_prove.py` | **PASS=193 FAIL=0** EXIT: SUCCESS |
| Soft Wave8 Specialist (+ nested Wave1–7) | **PASS=232 FAIL=0** |
| Live anon `:8788` | `/progress` `/api/progress` `/integration-health` `/sale-evidence-pack` → **403** |
| Honesty `/api/wolf/shell-whoami` (post beta reload) | `slice=wolf_permissions_audience_prove`; `permissions_audience_prove:true`; `four_layer_permissions:true`; `person_role_assignment_scope_permission_audience:true`; `sample_surfaces_empire_uma_progress:true`; `hidden_ne_permission:true`; `proven:false`; `ready:false` |
| Listeners | `:8787` up pid **15975** (untouched) · `:8788` reloaded for perms load (pid 68451) |

## Prove bars

| Bar | Status |
|-----|--------|
| Person→Role→Assignment→Scope→Permission→Audience in whoami/nav | **PASS** — `whoami.chain` + `whoami.permissions`; ROLE grants only (no hard-coded people in page logic) |
| Four layers on Empire + Uma + Progress | **PASS** — Matt all four; Devi Uma CAN_SEE+CAN_ACT only (no DETAIL/ACROSS); Haikal/client/unauth deny samples |
| Role matrix Matt/Devi/Haikal/client/unauth | **PASS** — chrome + live whoami |
| Hidden ≠ permission | **PASS** — nav-hidden Progress/Empire still URL/API 403 for Devi/Haikal/outsider |
| Soft Wave1–8 | **PASS** — Wave8 specialist soft prior PASS=232 |
| Honesty | **PASS** — proven=false ready=false (no invent Global Nav V1 READY) |

## Honesty

- CAP-CORE-11 stays **SPECIFIED** — not PROVEN/READY.
- CR `wolf-permissions-audience-architecture-20260922` — matrix evidenced; stays **OPEN** (no invent READY).
- CR `wolf-global-nav-design-system-20260922` stays **IN_PROGRESS** — do **not** declare Global Nav V1 READY (RHC screenshot debt separate).
- No money / Zayen / CF / Production mutation / Trading / parked FIN/HR/Devi commissioning.
- Claim honesty `proven=false` `ready=false`.

## In-pack files (additive / surgical)

- `scripts/core/wolf_shell.py` — perms slice; `PERM_LAYERS` / `ROLE_SURFACE_LAYERS` / `can_layer` / `permission_chain`; whoami.chain + permissions
- `dashboards/assets/sidenav.js` — cache `20260922-nav-perms`; `canLayer`; hello shows role from chain
- Soft Wave4–8 / RHC successor slice accepts (`permission`/`audience`)
- `scripts/tests/test_wolf_permissions_audience_prove.py`
- Beta `:8788` reload only (`:8787` untouched)

## Decision

Permissions / Audience Prove engineering **PASS**. Shell whoami/nav carries the clearance chain and four layers on sample Empire+Uma+Progress. Do **not** invent CAP PROVEN/READY or Global Nav V1 READY.

**EXIT: SUCCESS**
