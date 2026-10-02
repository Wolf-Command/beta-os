# CURSOR PACK — BZG-RECIPE-MULTI-OUTLET-1 (Beta only)

Workspace: `/Users/wolfterminal/beta-os`  
Branch: `build/wolf-command-rebuild` (local only — **no origin/push**)  
Prod `:8787`: **READ-ONLY**. Never mutate prod.  
`staff_ready=false` · `human_commissioned=false`

## Goal

One **BZG Recipe Builder** with **outlet context** (not seven apps). Haryanto (BZG Head Chef) can build real Rainforest / multi-outlet menus on Beta after Peaches credit-light verify.

## Read first (known anchors from prior packs)

- Desk href historically `/bzg/uma-blu/recipes`
- Catalog / recipe store: Owner pack names `catalog/bzg_recipes.sqlite` — **127 Uma Blu recipes / 756 lines** — **PRESERVE**; do not relabel BZG-wide. Prior box reconciliation also cites `wolf-system/uma-blu/recipes.sqlite` / prod `uma-blu-recipes` routes — reconcile to the live Beta path; do not invent a second database.
- Costing chain: `INGREDIENT → UNIT/CONVERSION → PURCHASE COST → SUBRECIPE → RECIPE → PORTION/YIELD → MENU ITEM → OUTLET → SELLING PRICE → FOOD COST → MARGIN`
- Missing ingredient cost = **INCOMPLETE COST** (never silent zero)
- Pack 09 pre-open outlets touched Pool Bar, Merah, Rooftop, Room Service, Catering, Blu Zone Restaurant — **reconcile Rainforest name vs registry** (`org_outlet_registry` / board title vs stored display_name). Do not hardcode seven outlet strings.
- Prior packs: `BZG-OUTLET-1` (registry + hierarchy scopes), Pack 08 recipe variance, Uma Blu BZG reconciliation (`/workspace/bzg/UMA-BLU-BZG-RECONCILIATION.md` on box mirror notes)
- Permissions: BZG Head Chef Assignment/Scope **server-side**; no finance/banking/Owner/HR/AMG/GGV

## Owner implement requirements (13 sections condensed)

1. **Outlet-aware single builder** — outlet selector extremely obvious; default sensible but **never silent wrong outlet**.
2. **Per selected outlet:** recipes, menu items, categories, status, costing, selling prices, food cost %, missing-cost exceptions, menu structure.
3. **Recipes:** one / multi / all-BZG outlets; store once; associate; no unnecessary duplication.
4. **Menus outlet-specific** — `RECIPE ≠ MENU ITEM ≠ OUTLET MENU`; shared recipe can have different menu item / price / portion per outlet.
5. **Shared ingredient master** (no seven masters).
6. **Nav:** Outlet dropdown + **All BZG** for Head Chef (catalogue + assignments, **NOT** a fake merged menu).
7. **Create recipe:** explicit outlet(s) + existing fields; Wolf costing from canonical purchase costs.
8. **Preserve 127 Uma Blu assignments** (and 756 lines).
9. **Outlets from canonical registry** (future outlets without rebuild) — do not hardcode seven.
10. **Reporting foundation only** — do not fake Rainforest FC / ESB theoretical / inventory variance if data not commissioned.
11. **Haryanto permissions** from Head Chef Assignment/Scope server-side.
12. **Engineering proof** (Owner §12) — tests + RESULT stamp under `state/final-completion/.../BZG-RECIPE-MULTI-OUTLET-1-RESULT.*`
13. **After Peaches verify:** send Haryanto to real Beta for real Rainforest menu work — **PASS or what blocked**; not commissioned merely for outlet switching.

## Engineering proof (must cover)

- Single builder with visible outlet context; no silent wrong-outlet default
- Registry-driven outlets (add/rename without hardcode rebuild)
- Uma Blu 127 / 756 preserved and still assigned correctly
- Recipe associate to one / multi / all-BZG without unnecessary duplication
- Menu item / price / portion can differ per outlet for a shared recipe
- Shared ingredient master
- INCOMPLETE COST when cost missing (never zero)
- Head Chef allow / deny scopes server-side (no finance/banking/Owner/HR/AMG/GGV bleed)
- Reporting surfaces refuse fake Rainforest FC / ESB theoretical / inventory variance when uncommissioned
- Prod `:8787` untouched; beta-only; local commit only

## Exit

`EXIT:0` when tests green **and** RESULT stamped.  
Commit **local pack slice only**. No push.  
Leave `staff_ready=false` and `human_commissioned=false`.

## Do not

- Contact Matt / ask Mac reconnect (`no_matt_reconnect_ask`)
- Mutate prod `:8787`
- Hardcode seven outlets
- Relabel Uma Blu recipes as BZG-wide
- Fake commissioned reporting numbers
- Mark human-commissioned for mere outlet switching

## Stamp / arm context (Peaches)

- Status now: **`PARKED_MAC_PIPE`**
- Resume when: **`PIPE_OK + PROVE_OK`**
- Arm: `cursor-agent -p --force --workspace /Users/wolfterminal/beta-os`
- Queue: `HUMAN_COMMISSIONING_ACTIVE` ahead of CE-CANCEL-UPLOAD-1 and Tours/Events
