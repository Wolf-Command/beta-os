# GROK REVIEW — Wolf Specialist Nav Wave 8 — 2026-09-22

**Run:** `BF-wolf-specialist-nav-20260922`  
**Peaches decision:** PASS (suite PASS=232; Wave7 PASS=197 soft; Wave6 PASS=165 soft; Wave5 PASS=147 soft; Wave4 PASS=134 soft; Wave3 PASS=111 soft; Empire PASS=175 soft; Shell PASS=94 soft; live anon 403 on Progress/Integrations/Sale + APIs; specialist soft redirect `/trading`→`/wolf`; honesty proven=false ready=false; :8787 pid 15975 untouched)  
**Head:** `f3ab8f7` deferred · Production `:8787` not mutated (pid 15975 unchanged)  
**Claim:** `bf-wolf-specialist-nav-20260922` · bound beta · proven=false · ready=false

## Evidence

| Check | Result |
|-------|--------|
| `test_wolf_specialist_nav.py` (direct runner) | **PASS=232 FAIL=0** EXIT: SUCCESS |
| Wave-7 `test_wolf_system_nav.py` | **PASS=197 FAIL=0** (soft prior) |
| Wave-6 `test_wolf_intel_nav.py` | **PASS=165 FAIL=0** (soft) |
| Wave-5 `test_wolf_amg_nav.py` | **PASS=147 FAIL=0** (soft) |
| Wave-4 `test_wolf_ggv_nav.py` | **PASS=134 FAIL=0** (soft) |
| Wave-3 `test_wolf_bzg_uma_nav.py` | **PASS=111 FAIL=0** (soft) |
| Wave-2 `test_wolf_empire_home.py` | **PASS=175 FAIL=0** (soft) |
| Wave-1 `test_wolf_shell_tokens.py` | **PASS=94 FAIL=0** (soft) |
| Live anon `:8788` `/progress` `/api/progress` `/integration-health` `/sale-evidence-pack` | **403 / 403 / 403 / 403** |
| Live soft redirect `/trading` | **302 Location: /wolf** |
| Honesty `/api/wolf/shell-whoami` | `slice=wolf_specialist_nav_v8`; `specialist_not_primary:true`; `specialist_soft_redirect_empire:true`; `system_home_soft_land_progress:true`; `staff_hide_system_admin:true`; `haikal_landing_content:true`; `proven:false`; `ready:false` |
| Listeners | `:8787` up pid **15975** (untouched) · `:8788` up (restarted for Wave8 load; pid 58690) |

## Wave-8 bars

| Bar | Status |
|-----|--------|
| trading / travel / spartacus / mila / amanda / kuta-rates **not** in primary `#wolfnav` IA | **PASS** |
| Owner whoami IA = HOME / BUSINESSES / INTEL / SYSTEM only (no specialist top-level) | **PASS** |
| Soft redirect specialist entry → `/wolf` (no new sprawl pages) | **PASS** |
| Hidden ≠ deleted (redirect preserves route-into-Wolf; capability not wiped) | **PASS** |
| Wave1–7 soft regressions green (System/Intel/AMG/GGV/BZG/Empire/Shell) | **PASS** |
| Staff hide SYSTEM admin via nav; landings retained | **PASS** |
| Breadcrumbs / UP / HOME grammar unchanged on primary surfaces | **PASS** |
| One `#wolfnav` on Progress / Empire | **PASS** |
| Anon Progress/API/Integrations/Sale 403 | **PASS** |

## Honesty

- CAP-CORE-11 stays **SPECIFIED** — not PROVEN/READY.
- CR `wolf-global-nav-design-system-20260922` stays **IN_PROGRESS** (Wave8 evidence in this review).
- CR `wolf-global-nav-responsive-hierarchical-20260922` stays **OPEN** (screenshot + expanded deny-matrix debt).
- No money / Zayen / CF / Production mutation / Trading execution.
- No invent PROVEN/READY. Claim honesty `proven=false` `ready=false`.
- No new dashboard sprawl — specialist boards soft-redirect into Empire; primary IA unchanged shape.

## Specialist soft-land decision (documented)

**Primary:** trading / travel / spartacus / mila / amanda / kuta-rates retired from `#wolfnav` primary IA.  
**Soft redirect:** `/trading` (+ `.html` / `/dashboards/…` variants and peers) → `/wolf` (Empire HOME).  
Hidden ≠ permission — direct URL still subject to API/auth fail-closed after soft-land.  
No Trading execution desk invented; Flint reserved remains refused elsewhere.

## In-pack files (additive / surgical)

- `scripts/core/wolf_shell.py` — Wave8 slice, HIDDEN specialist constants, soft-redirect helpers, honesty flags
- `dashboards/assets/sidenav.js` — HIDDEN_SPECIALIST_PRIMARY map + cache `20260922-nav-specialist`
- `scripts/serve_beta.py` — surgical Wave8 specialist soft redirects (dirty WIP preserved)
- `scripts/tests/test_wolf_specialist_nav.py` + Wave4–7 soft successor slice asserts

## Decision

Wave-8 Specialist Nav engineering **PASS**. Migration-order Wave 8 complete for primary-IA specialist removal — do not invent READY. Responsive screenshot V1 READY pack remains later debt.

**EXIT: SUCCESS**
