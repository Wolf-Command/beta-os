# GLOBAL-APP-SHELL-SPEC — Wolf application shell (P0)

Generated: 2026-09-30T10:59:39+08:00 (Asia/Makassar / WITA)  
Executor: Peaches · machineId `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
Bound: **Beta only** (`serve_beta.py` / `beta-os`) · Prod `:8787` READ-ONLY  
Honesty: `staff_ready=false` · `human_commissioned=false` · no Exit Report · never claim REBUILT+PROVEN

## Purpose

Unify navigation across boards so people stop bouncing through inadequate per-board nav.  
One chrome (`#wolfnav` / `sidenav.js`) · Target IA · clearance-driven menus · phone + desktop.

## Authority chain (People ≠ Roles)

Canonical (RULE locked 2026-09-24):

```
PERSON → ROLE/POSITION → ASSIGNMENT → SCOPE → PERMISSION → AUDIENCE
```

Task shorthand PERSON→ASSIGNMENT→ROLE→SCOPE→PERMISSION maps to the same objects;  
**do not invent person-name couplings** in page logic. Grants are by ROLE / ASSIGNMENT / SCOPE.

| Layer | Meaning | Shell use |
|-------|---------|-----------|
| PERSON | Who is signed in | whoami.person_id; hello label |
| ROLE / POSITION | Job seat (not a person name) | whoami.roles; ROLE-* codes |
| ASSIGNMENT | Occupancy of a position | whoami.assignments[] |
| SCOPE | Org boundary (entity/site/BU) | whoami.scopes[]; filter destinations |
| PERMISSION | Four layers CAN_SEE · CAN_ACT · CAN_SEE_DETAIL · CAN_SEE_ACROSS_SCOPE | whoami.permissions |
| AUDIENCE | Chrome projection class (OWNER / OPERATOR / …) | whoami.audience; pages[] |

**Hidden ≠ permission.** Nav visibility never replaces API auth.

## IA derivation (anti-drift)

| Source | Role |
|--------|------|
| `scripts/core/wolf_shell.py` `IA_TREE` | **Beta SoT** for primary chrome sections HOME · BUSINESSES · INTELLIGENCE · SYSTEM |
| `dashboards/assets/sidenav.js` `IA_TREE` | Client mirror — must stay aligned (cache-token bump on change) |
| `state/final-completion/p0-v1/V1-SURFACE-MANIFEST-DRAFT.json` | V1 recovery input (e.g. Trading / Fitness Owner re-entry) — **feeds** IA; does not replace it |
| `state/final-completion/p0-v1/SHELL-IA-BUSINESSES.json` | Optional overlay notes; businesses still **derived** from IA_TREE |

Do **not** maintain a third hardcoded Boards list on individual HTML pages.

### Owner personal surfaces (PARTIAL)

| Surface | Route | IA |
|---------|-------|-----|
| Trading (Owner) | `/owner/trading` | HOME · key `owner_trading` · audience owner · migration_state PARTIAL |
| Fitness (Owner) | `/owner/fitness` | HOME · key `owner_fitness` · audience owner · migration_state PARTIAL |

Wave-8 soft-redirect retired travel/mila/amanda/kuta-rates; Trading/Fitness re-entered as Owner HOME (not specialist sprawl).

## Business switcher

**Problem:** Assignment context switcher alone is insufficient when org DB collapses Owner into one primary assignment href (`/wolf`). People still need AMG / BZG / GGV / Owner jumps without opening Boards.

**Behavior:**

1. Build `businesses[]` from **IA_TREE** (Owner/Empire + BUSINESSES items), filtered by whoami-allowed pages/scopes — not by person name.
2. Show `#wolfnav-biz` when ≥1 authorised business; interactive switch when ≥2 (`business_switcher=true`).
3. Chips (short labels): **Owner** · **GGV** · **AMG** · **BZG** · **Uma Blu** (when in IA + allowed).
4. Active chip = longest href/alias prefix match on current path (e.g. `/owner/trading` → Owner; `/bzg/uma-blu/bills` → Uma Blu).
5. Click → navigate to business home href only if `pageAllowed` (same fail-closed rule as Boards).
6. Distinct from assignment **Context** switcher (`#wolfnav-ctx`): Context = multi-assignment role/scope seats; Business = entity homes from IA.
7. Phone: horizontal scroll chip row; Desktop: same chips in top chrome row. One shell — not a separate mobile product.

## Direction + breadcrumbs

Every surface: **UP** (parent) · **BACK** (logical prior / trail) · **HOME** (authorised landing).  
Breadcrumbs hierarchy-aware; Trading/Fitness crumbs: `HOME › Trading|Fitness (Owner)`.

## Phone + desktop

| | Desktop | Phone (≤860px) |
|--|---------|----------------|
| Nav | Side/top Boards drawer + full chrome | Compact top bar; Boards closed by default; drawer + scrim |
| Business | Chip row in `#wolfnav` | Same chips, overflow-x auto, touch-safe ≥44px |
| Direction | UP/BACK/HOME visible | Same; may wrap under brand |
| Auth | Unchanged | Unchanged |

## Non-goals / constraints

- No prod `:8787` mutation (pid 15975 sacred)
- No HR work · no Exit Report · no staff_ready / human_commissioned invent
- No second Boards menu · no weakening auth · no live Trading broker
- Credit conservation: one focused shell pack (SPEC + business switcher + Owner crumb/IA consistency)

## Acceptance (this pack) — PARTIAL

- [ ] SPEC landed at this path
- [ ] whoami exposes `businesses` + `business_switcher` derived from IA ∩ clearance
- [ ] Visible `#wolfnav-biz` on Owner Empire / Trading / Fitness after hard-refresh
- [ ] Trading + Fitness in Owner HOME IA + crumbs/parent wired (sidenav mirror + wolf_shell)
- [ ] Cheap tests pass · Beta only
- [ ] `migration_state=PARTIAL` · not REBUILT+PROVEN

## Related canon

- `docs/RULE-Wolf-Global-Navigation-Design-System-2026-09-22.md`
- `docs/RULE-Wolf-People-Are-Not-Roles-2026-09-24.md`
- `docs/deliveries/GROK-SPEC-WOLF-GLOBAL-SHELL-2026-09-22.md`
- `docs/canon/ROLE-POSITION-ASSIGNMENT-TRANSITIONAL.md`
- Transfer: `transfer/TRANSFER-TRADING-SPEC.md` · `transfer/TRANSFER-FITNESS-SPEC.md`

## Follow-on (2026-09-30 nav authority PARTIAL)

Chrome `#wolfnav-biz` is **AUTHORITY_CHROME**: prefers `nav_authority.businesses` (Assignment/Role/Scope); falls back to IA∩pages `businesses` with honesty stamp. NOT sole source · NOT LIVE_USABLE · migration_state PARTIAL. See `NAV-AUTHORITY-SPEC.md`.

