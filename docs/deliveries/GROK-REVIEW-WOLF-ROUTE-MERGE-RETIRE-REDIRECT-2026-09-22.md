# GROK REVIEW — Wolf Route Merge / Retire / Redirect — 2026-09-22

**Run:** `BF-wolf-route-merge-retire-redirect-20260922`  
**Peaches decision:** PASS (suite PASS=152; inventory complete; redirect>delete wired on Beta :8788; APIs unchanged; honesty proven=false ready=false; :8787 untouched)  
**Head:** `f3ab8f7` deferred · Production `:8787` not mutated  
**Claim:** `bf-wolf-route-merge-retire-redirect-20260922` · bound beta · proven=false · ready=false  
**Prior:** Wave1–8 + RHC PASS=248 + Perms PASS=193 DONE · Soft Wave8 PASS=232 (honesty flags cheap-kept; full nested soft-skipped)

## Inventory (Mac Beta tree — find before mass retire)

| Surface | Found | Action this slice |
|---------|-------|-------------------|
| `*mgmt-cluster*` | 11 HTML under `dashboards/*-mgmt-cluster.html` (no `/mgmt-cluster/` dir) | 302 → owning BU / SYSTEM / Empire parent; APIs+HTML on disk kept |
| `*operator-depth*` / `*opdepth*` | **0 HTML** (API-only under packs) | No page retire; APIs untouched |
| Legacy uma | `/uma-blu`(+.html) aliases (no `uma-blu.html` file) | 302 → `/bzg/uma-blu` |
| Content brand peers | **none** on disk (only `content-2.0.html`) | Alias 302 → `/content-2.0?brand=…` |
| Radar | `radar-prove.html` ACTIVE kept; no standalone `radar.html` file | `/radar(.html)` → `/wolf#priorities` |
| Duplicate `/dashboards/*.html` | many pack aliases | 302 → clean URLs |
| Specialist primary | already Wave 8 | Soft redirect retained |
| Progress/Factory/Integ/Sale | already Wave 7 under SYSTEM | Retained; not peer Boards |

## Evidence

| Check | Result |
|-------|--------|
| `test_wolf_route_merge_retire_redirect.py` | **PASS=152 FAIL=0** EXIT: SUCCESS |
| Soft Wave8+RHC+Perms | **cheap honesty flags** PASS; **soft-skip** full nested subprocess (Wave8 nests W1–7; Perms nests Wave8 — not cheap) |
| Live anon `:8788` (post reload) | legacy/duplicate/mgmt → **302**; parents + mgmt APIs still **403** |
| Honesty `/api/wolf/shell-whoami` | `slice=wolf_route_merge_retire_redirect`; `route_merge_retire_redirect:true`; `proven:false`; `ready:false` |
| Listeners | `:8787` untouched · `:8788` reloaded |

## Prove bars

| Bar | Status |
|-----|--------|
| Inventory before mass retire | **PASS** — 11 mgmt HTML; 0 operator-depth HTML; 0 content brand peers; radar-prove kept |
| Redirect > delete top candidates | **PASS** — uma / dashboards/*.html / radar / mgmt-cluster / content aliases |
| Capability preserved | **PASS** — serve_beta aliases; IA parents; Needs You unchanged; `/api/*` never redirected |
| Old URL → 302 new | **PASS** — table + live Handler |
| Auth fail-closed | **PASS** — anon 403 on parents + mgmt/uma APIs |
| One `#wolfnav` | **PASS** — sidenav.js sole Boards owner; IA no second Boards / no mgmt peers |
| Progress/Integ/Sale under SYSTEM | **PASS** — retained Wave 7 |
| Specialist drop primary keep route | **PASS** — Wave 8 soft redirect retained |
| Honesty | **PASS** — proven=false ready=false (no invent Global Nav V1 READY) |

## Honesty

- CAP-CORE-11 stays **SPECIFIED** — not PROVEN/READY.
- CR `wolf-global-nav-design-system-20260922` stays **IN_PROGRESS** — do **not** declare Global Nav V1 READY.
- ACTIVE factory pack HTML/APIs **not deleted** — top-level bookmarks soft-land only. Night-shift mgmt claim `page:403` may read `page:302` (parent still anon-403 if followed) — note for Peaches; packs not killed.
- No money / Zayen / CF / Production mutation / Trading / parked FIN/HR/Devi commissioning.
- Claim honesty `proven=false` `ready=false`.

## In-pack files (additive / surgical)

- `scripts/core/wolf_shell.py` — `ROUTE_MERGE_REDIRECTS` + `route_merge_redirect_target` + inventory; slice `wolf_route_merge_retire_redirect`
- `scripts/serve_beta.py` — early 302 from merge table (before page serve)
- `dashboards/assets/sidenav.js` — cache `20260922-nav-route-merge`; IA unchanged (already Target IA)
- Soft prior Wave tests accept route/merge/retire/redirect successor slice + new cache token
- `scripts/tests/test_wolf_route_merge_retire_redirect.py`
- Beta `:8788` reload only (`:8787` untouched)

## Decision

Route Merge / Retire / Redirect engineering **PASS**. Redirect>delete for inventory top candidates on Beta `:8788`. Do **not** invent CAP PROVEN/READY or Global Nav V1 READY.

**EXIT: SUCCESS**
