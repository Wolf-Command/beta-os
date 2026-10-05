# HARYANTO-UX — Recipe Builder human-test repair

You are the Beta engineer. Workspace: /Users/wolfterminal/beta-os
Branch: build/wolf-command-rebuild (dirty). Do not commit. Do not push. Do not merge.

## Locks
- Prod is sacred. Python pid 15975 on 127.0.0.1:8787 must stay that pid. Do not restart it. Do not edit its database.
- Beta listener is Python pid 76967 on 127.0.0.1:8788 (started after 15:50 WITA). Do not reload, kill, or start a second listener. If Python must change to serve the repair, write RELOAD_REQUIRED: yes in the result and stop. Peaches reloads.
- Do not modify venue daily close VDC-470e741f-d889-437a-9a40-1ec9c083fb95. It stays EXCEPTION, cash 3225000, variance -125000, updated_at 2026-10-03T13:47:39Z.
- Do not touch petty cash, finance pages, GGV receipts, the God Mode register, or Owner Home.
- Do not copy /Users/wolfterminal/beta-os/catalog/content_library.sqlite or anything into catalog/backups. Disk is nearly full. Tests use a tempfile sqlite, then delete it.
- Do not invent ingredients, recipes, menu items, prices, covers, or costs. Missing cost is INCOMPLETE COST, never zero.
- Do not hardcode Carolus Haryanto, carolus.haryanto@gmail.com, or a person id.
- Do not grant venue.close.read. Do not widen ROLE-BZG-HEAD-CHEF.
- staff_ready stays false. Do not mark anything human commissioned. Do not edit GOD-MODE-REGISTER.
- Leave cursor-agent pid 63443 alone.
- No --trust. You are already the worker.

## What failed
Haryanto (PERS-HARIYANTO, role ROLE-BZG-HEAD-CHEF, assignment ASG-HARIYANTO-HEAD-CHEF-1, scope SCOPE-BZG-FB) used Beta. Recipe Builder loaded. Outlet registry loaded. Rainforest and Pool Bar showed PRE-OPENING. Rainforest showed zero recipes. A link sent him to /bzg/uma-blu and he got Access Denied. Menu back dumped him into the recipe list. The ingredient field is a plain text box.

/bzg/uma-blu is the ops/close surface. Head Chef home is /bzg/recipe-builder. He lacks venue.close.read on purpose. Do not give it to him. Remove or stop emitting any Head Chef navigation that targets /bzg/uma-blu. Access Denied must not be the way back works.

## 1. Outlet status, canonical only
Live table org_outlet_registry in catalog/content_library.sqlite, and the seed in scripts/core/bzg_outlet_registry.py, must match.

Set status OPEN, and only status, for:
- BZG-UMA Uma Blu (already OPEN; leave it)
- BZG-RAIN Rainforest
- OU-BZG-RAIN-POOL Pool Bar

Leave PRE-OPENING:
- BZG-MERAH, BZG-ROOF, BZG-RS, BZG-CAT

Do not rename outlets. Do not edit org_brands. Do not patch HTML strings to fake the status. Derived surfaces read list_outlets. OPEN does not mean invent sales or history.

## 2. Rainforest menu truth
outlet_menu_items is currently 0 for every outlet. recipe_outlet_links for BZG-RAIN and the pool bar are 0. Recipes (127) and links (127) are all BZG-UMA.

Search authorised sources already on this machine (recipe db, Alchemist exports, docs). Read only. If a real Rainforest or Pool Bar menu exists, reconcile it: where a menu item has no recipe, the page says MENU ITEM EXISTS / RECIPE MISSING. If no authorised menu exists, the open outlet must say that Wolf has no menu items and no recipes for it yet. Do not copy Uma recipes onto Rainforest. Do not invent dishes.

## 3. Ingredient type-ahead
Canonical master is catalog/bzg_recipes.sqlite table ingredient_master (292 rows). One shared BZG master. No second master. No alias column today. Do not create duplicate ingredients for case or spacing.

Replace dashboards/bzg-recipe-builder.html plain input.l-name with a searchable combobox:
- Click shows useful options from the master.
- Typing narrows immediately, case insensitive, extra spaces ignored.
- Rank: exact, then starts-with, then word-start, then contains.
- c / ca / car must narrow. Real master includes carrot, capsicum, caramelized onion, celery stick. Do not add cabbage, cashew, or cauliflower unless they already exist.
- Selecting binds the canonical ingredient id internally and shows the human name only. Never show the id.
- Surface default_unit, purchase_cost when present, and cost status. Null cost is INCOMPLETE COST, never 0. Do not guess a cost.
- Preselect default_unit. Quantity is what the chef types. Unit selector only offers the standard unit and real conversion units that already exist. No meaningless units.
- Add ingredient adds another row with the same behaviour. A row can be removed before save. Block accidental duplicate ingredient lines. If a second line for the same ingredient is a real preparation stage, require an explicit stage, do not silently merge or double.
- Unknown text shows NO MATCHING INGREDIENT. Do not insert into ingredient_master from recipe typing. He has ingredient.read, not a create right. Do not add ingredient.create. Point at the governed request only if one already exists for this role; otherwise say a new ingredient has to be requested and stop.
- Existing recipe_lines store name, not ingredient_id (756 lines). Keep those lines readable. New saves store the canonical id as well as the name. Do not destroy the 756 lines.

## 4. Chef workflow clarity
On the builder it is obvious, in plain language: which outlet, which recipe, which outlets use it, ingredients, quantity, unit, ingredient cost or INCOMPLETE COST, recipe cost, portion cost, this outlet's selling price, food cost percent, and what is missing. No engineering words. Do not invent a selling price. Missing price stays missing, and food cost percent stays missing with it.

Shared model stays: one ingredient master, shared recipes, outlet-specific menu item / price / availability. Do not duplicate a recipe because two outlets might sell it.

## 5. Navigation
Audit Outlet Registry, Recipe Builder, Recipes, Menu, Cost Gaps, New Recipe, outlet switch, Back, Up, Home, Here.
Menu back must return to the previous real surface, not jump to the recipe list unless that list was actually previous. Keep outlet context. No dead end. No link that produces Access Denied for this role.

## 6. Tests
New test under scripts/tests/. Temp sqlite only, removed at the end. No catalog copy.
Prove: Rainforest and Pool Bar OPEN; Merah, Rooftop, Room Service, Catering PRE-OPENING; Uma Blu still OPEN.
Prove type-ahead narrowing on real master names (read-only select, or rows inserted into the temp db from those real names). Prove canonical id binding, no duplicate insert, null cost is not stored as 0, unknown name does not create a row.
Prove a Head Chef permission fixture still has no venue.close.read and the builder nav does not target /bzg/uma-blu.
Do not run scripts/tests/test_petty_cash_record_out_20261004.py. Do not modify the live almond-milk recipe.

## Result
Write /Users/wolfterminal/beta-os/state/reliability/HARYANTO-UX-RESULT-2026-10-04.md
Include: status, files changed, tests passed/failed, outlet statuses after the change, whether a real Rainforest menu was found (path or NOT FOUND), RELOAD_REQUIRED yes or no, confirmation prod pid 15975 was not touched and the protected close was not written.
