# NAV-AUTHORITY-SPEC — Assignment/Role/Scope-derived navigation (P0)

Generated: 2026-09-30T12:23:21+08:00 (Asia/Makassar / WITA)  
Executor: Peaches · machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
Bound: **Beta only** · Prod `:8787` READ-ONLY  
Honesty: `staff_ready=false` · `human_commissioned=false` · no Exit Report · PARTIAL

## Gap (b3739a7 global shell PARTIAL)

| Mode | How nav is built today | Status |
|------|------------------------|--------|
| **IA ∩ pages (transitional)** | `IA_TREE` businesses filtered by `whoami.pages` from `AUDIENCE_PAGES[audience]` | Chrome `#wolfnav-biz` still uses this |
| **Audience bridge** | `audience_for_person` prefers org assignment roles for finance/content seats; else `PERSON_AUDIENCE` person map | People≠Roles debt remains for some fixtures |
| **Authority (target)** | `PERSON → ROLE/POSITION → ASSIGNMENT → SCOPE → PERMISSION → AUDIENCE` | **PARTIAL this pack** — `nav_authority` parallel field |

**Problem:** Staff replacement / new outlets / new companies must not require engineering edits to person-name maps or hard-coded Boards lists. IA∩pages alone cannot survive that.

## This pack (smallest Beta step)

1. `authority_nav_from_assignments(assignments)` — chips/items from **ROLE + SCOPE only** (person_id ignored).
2. `authority_nav_for_person(person_id)` — loads ACTIVE org assignments then derives.
3. `build_whoami` / `GET /api/wolf/shell-whoami` expose `nav_authority` alongside transitional `businesses`.
4. Unit test **staff swap**: same ROLE+SCOPE on PERS-A vs PERS-B → identical `nav_authority`.
5. SPEC + honesty flags: `ia_intersect_pages_transitional=true`, `authority_nav_partial=true`.

### Not yet (deferred)

- ~~Sidenav paintBusiness prefer `nav_authority.businesses`~~ → AUTHORITY_CHROME (prefer+fallback; sole source still deferred)
- Delete `PERSON_AUDIENCE` / fixture `PERSON_ASSIGNMENTS` couplings
- Full PERMISSION-layer filter on every IA item
- Claim REBUILT+PROVEN / staff_ready

## Staff-swap acceptance (unit)

```
assignments(ROLE-X, SCOPE-Y) on PERS-OLD == assignments(ROLE-X, SCOPE-Y) on PERS-NEW
⇒ nav_authority.businesses + items identical
⇒ no person_id / person display name in derivation keys
```

## Route recovered caps (ROLE, not person)

| Seat (example person) | ROLE / SCOPE | Authority nav items |
|----------------------|--------------|---------------------|
| Zayen | ROLE-AMG-FINANCIAL-CONTROLLER · SCOPE-AMG-FINANCE; ROLE-BZG-FINANCIAL-CONTROLLER · SCOPE-BZG-FINANCE | /amg/finance · /bzg/finance · chips AMG+BZG |
| Amanda | ROLE-GGV-FINANCE-OPERATOR · SCOPE-GGV-FINANCE (+ Content mgmt) | /ggv/finance · chip GGV |
| Hariyanto | ROLE-BZG-HEAD-CHEF · SCOPE-BZG-FB | /bzg/recipe-builder · chip BZG |
| Content crew | ROLE-CONTENT* · SCOPE-GGV-CONTENT* | /content-2.0 · seats/* |
| Devi | ROLE-BZG-FB-OPS-LEAD · SCOPE-BZG-UMA | /bzg/uma-blu · chip Uma/BZG |

## Related

- `GLOBAL-APP-SHELL-SPEC.md` (prior PARTIAL — IA∩clearance business switcher)
- `docs/RULE-Wolf-People-Are-Not-Roles-2026-09-24.md`
- `scripts/core/organisation.py` · `staffing.py` · `scope.py` · `rbac.py` · `identity.py`


## Chrome wire (2026-09-30 AUTHORITY_CHROME)

- `#wolfnav-biz` / `paintBusiness` prefers `nav_authority.businesses`.
- Fallback: transitional IA∩pages `businesses` + honesty stamp `data-nav-source=ia_intersect_pages_transitional`.
- Status: **AUTHORITY_CHROME** (WIRED_PARTIAL). NOT sole Assignment/Role/Scope source. NOT LIVE_USABLE.
- Cache: `20260930-nav-authority-chrome` · generated 2026-09-30T12:32:39+08:00
