# HEADCHEF-1 result

29 Sep 2026. Beta only, branch `build/wolf-command-rebuild`. BZG Head Chef (Hariyanto) canonical access + Recipe Builder. Production `:8787` pid **15975** untouched. Cloudflare not mutated. `BETA_AUTH_MODE` unset (unchanged). Commits local only. `staff_ready=false`. Commissioning Work Item remains **HELD_UNTIL_CF_ACCESS** — not activated (Peaches activates after allow/deny pass).

Decision served: 2026-09-29 PICK HEADCHEF-1 in `~/.openclaw/wolf-output/decisions.md` (extends CAP-BZG-06 / UMAREAL-1).

## Identity / assignment / scope

| Id | Value |
| --- | --- |
| Person | `PERS-HARIYANTO` |
| Display | Hariyanto |
| Legal | Carolus Haryanto |
| AuthIdentity | `AUTH-HARIYANTO-EMAIL` · provider `email` · `carolus.haryanto@gmail.com` |
| Role | `ROLE-BZG-HEAD-CHEF` · Head Chef · `DEPT-BZG-FB` |
| Position | `POS-BZG-HEAD-CHEF-1` · entity `ENT-BZG` · brand/location **NULL** (not one outlet) |
| Assignment | `ASG-HARIYANTO-HEAD-CHEF-1` |
| Scope | `SCOPE-BZG-FB` upgraded to **entity** `ENT-BZG` (+ department `DEPT-BZG-FB`) so current and future BZG brands resolve via `org_brands` membership — no outlet names in grants |
| Commissioning WI | `WI-76be899c-8445-47bc-8994-becd36a556e7` · `COMM-HARIYANTO-RECIPE-BUILDER` · `HELD_UNTIL_CF_ACCESS` |
| Maciej | `PERS-MACIEJ` · `AUTH-MACIEJ-EMAIL` · `barefeet14@hotmail.com` · **zero assignments** · operational routes 403 |

CF allow evidence: `state/access-evidence/cf-beta-allow-20260929.json` (Matt confirmed; not CF API verified).

## Permission matrix

### ALLOW (`ROLE-BZG-HEAD-CHEF` via `org_role_permissions` only)

| Code | Purpose |
| --- | --- |
| `recipe.read` | Recipe Builder + recipe list/detail |
| `recipe.create` | Create recipes |
| `recipe.edit` | Edit recipes / ingredients / yields / method |
| `recipe.cost.read` | Food cost %, margins, portion cost |
| `ingredient.read` | Ingredient lines |
| `menu.price.read` | Selling price **read-only** (no chef edit policy) |
| `supplier.product.read` | Supplier/product info for costing |
| `recipe.exceptions.read` | Cost-missing / completeness exceptions |
| `work.read` / `work.create` / `work.update` / `work.complete` | Kitchen My Work |
| `evidence.record.read` / `evidence.record.submit` | Evidence |
| `approval.request` | Propose changes that need approval (sell price stays propose-only) |

### DENY (asserted not on role; HTTP 403 in suite)

payment.approve · payment.execute · vendor.bank.change · bzg.pr.payment_approve · progress.read · organisation.role.read · organisation.person.read · approval.decide · venue.close.verify · atrium.ledger.read · finance.nota.read · finance.invoice.read · Owner `/wolf` · HR payroll · AMG/GGV finance desks · Uma Today ops (`venue.close.read` not granted)

Sell-price **edit** refused (403 / PermissionError). Chef cannot invent unit costs.

## Recipe Builder

- Page: `/bzg/recipe-builder` (desktop 1024 + phone 390)
- APIs: `GET/POST /api/bzg/recipe-builder/recipes`, `PUT …/recipes/{id}`, `GET …/exceptions`
- Store: `catalog/bzg_recipes.sqlite` (temp via `RECIPE_BUILDER_DB` in tests)
- Import: 127 dishes from V1 `recipes.sqlite` (idempotent, provenance kept). Tests fall back to `recipes-export.json` under the canonical guard.
- Costing: reuses Uma real purchase/card matching. Missing → **"cost missing"**, never 0 or a guess.
- Cost gaps today: **19** recipes with incomplete cost (examples: Blu Buddha Bowl — Tempeh, Big Blu Breakfast — Plant Vegan/Vegetarian, Classic/Fire Omelette).
- Owner CAP-BZG-06 `/bzg-bom-yield` skeleton unchanged (Owner-only empty framework).

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_headchef1_20260929.py` | SUMMARY pass=**92** fail=**0**, RESULT: PASS |
| `scripts/tests/test_staff_access_20260928.py` | pass=274 fail=1 (`Zayen direct Atrium Finance` — atrium sidecar/guard flake under test; not loosened) |

## Shots (`docs/wolf/ops/shots/`)

- `headchef1-recipe-list-desktop.png` / `headchef1-recipe-list-phone.png`
- `headchef1-recipe-detail-desktop.png` / `headchef1-recipe-detail-phone.png`
- `headchef1-recipe-create-desktop.png` / `headchef1-recipe-create-phone.png`
- `headchef1-denied-desktop.png` / `headchef1-denied-phone.png`

## My Work / commissioning

Held WI is **not** in Hariyanto's active My Work and **not** in the War Room active human queue. Note: activate when Matt confirms CF allow (confirmed 2026-09-29) — Peaches activates only after Person/AuthIdentity, Head Chef Assignment/Scope, real Recipe Builder, and server-side allow/deny checks pass. **Not activated in this session.**

## Pids

| Process | Pid |
| --- | --- |
| Production `:8787` | 15975 (unchanged) |
| Beta `:8788` | 22575 (replaced 13176; `BETA_AUTH_MODE` still unset) |

## staff_ready

**false** (Hariyanto, and unchanged for Devi / content / Zayen).

RESULT: PASS (engineering). Human commissioning PENDING / HELD.
