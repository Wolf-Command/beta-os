# HARYANTO-RECIPE-FINISH

Finish the existing BZG Recipe Builder on Beta so Haryanto can bug-test a real recipe. This is not a new architecture.

Workspace: /Users/wolfterminal/beta-os only.
Tip must stay 0b0e50da410d7158777871ae240c7e757502f5d3. No commit. No push. No merge.

## Required on the existing builder

- An existing Uma Blu recipe opens.
- Real ingredient typeahead selection (already passed as a component; do not rebuild it).
- Quantity and unit can be set and saved.
- Save persists. Reload shows the same recipe.
- Cost uses the stored ingredient cost. If cost is missing, say cost unknown. Do not invent a price.
- Menu and Back work.
- Outlet switch uses the registry. Uma Blu has recipes. Rainforest and Pool Bar stay honest empty if no menu source exists. Do not copy Uma recipes across.
- Head Chef must not get Access Denied on his own builder. Do not grant him work.update.
- Desktop must not stretch a phone card across the page. Function first.
- Phone layout must still be usable.
- No GL, journals, account codes, or engineering labels on the staff page.

## Hard limits

- Do not invent Rainforest or Pool Bar menus or recipes.
- Do not create Almond Milk as a recipe.
- Do not fabricate operational rows.
- Do not copy catalog/content_library.sqlite. Tests use a temp sqlite.
- Do not touch venue closes VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5, VDC-470e741f-d889-437a-9a40-1ec9c083fb95, or VDC-87202768-55af-4c8e-abc3-382a5496b8c6.
- Outlets Uma Blu, Blu Zone Restaurant & Bar / Rainforest, and Pool Bar stay OPEN. Do not revert.
- staff_ready stays false. Do not mark human commissioned.
- On-demand spend stays off.
- Beta reload only if Python changed, and only one listener on 127.0.0.1:8788. Never touch prod pid 1297 on 127.0.0.1:8787.
- No new close. No fake rows. No live catalog copy.

## Result

Write state/reliability/HARYANTO-RECIPE-FINISH-RESULT-2026-10-04.json with what was proved, the exact staff link, and what is still not proved.
