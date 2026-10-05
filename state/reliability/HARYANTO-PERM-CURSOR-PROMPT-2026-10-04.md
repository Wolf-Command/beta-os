# Head Chef permission leak — 4 Oct 2026

You are editing ONLY /Users/wolfterminal/beta-os.

Finish this slice, then stop. One role change. Do not invent a second permission system.

## What is wrong

Head Chef (`ROLE-BZG-HEAD-CHEF`) is granted `work.update`. That capability is the gate inside `set_opening_float_ops` and `count_petty_ops` in `scripts/core/uma_ops_console.py` (`_require_ops_permission(..., "work.update")`). The grant is on the role, seeded by `EXISTING_GRANTS` in `scripts/migrations/migrate_headchef1_20260929.py` and stored on `org_role_permissions` for that role. The active assignment is `ASG-HARIYANTO-HEAD-CHEF-1` on scope `SCOPE-BZG-FB` for `ENT-BZG`.

Because the gate is `work.update`, a Head Chef principal can change opening float and petty count. That is the leak.

## Fix

Fix Role / Assignment / Scope so Head Chef does not receive `work.update`.

- Remove `work.update` from `ROLE-BZG-HEAD-CHEF` only. Leave every other role that legitimately has `work.update` unchanged.
- Do not remove recipe permissions: `recipe.read`, `recipe.create`, `recipe.edit`, `recipe.cost.read`, `recipe.exceptions.read`. Also leave the other non-cash Head Chef grants (`ingredient.read`, `menu.price.read`, `supplier.product.read`, `work.read`, `work.create`, `work.complete`, `evidence.record.read`, `evidence.record.submit`, `approval.request`) unless you prove one of them is what actually authorizes opening float, petty count, daily close, finance, or another cash control. If you prove that, remove only that cash-control capability from Head Chef and say which one.
- He must keep recipe access. He must not be able to change opening float, petty count, daily close, finance, or other cash controls.
- Do not patch by email. Do not hardcode his email or person id. Do not special-case one person in `serve_beta.py` or the ops console. The deny has to come from the role grant (and assignment/scope only if the role grant is not what delivers `work.update`).
- Update the seed/migration list so a later apply does not put `work.update` back on Head Chef. Update any Head Chef test that currently expects `work.update` to be allowed, so it expects the deny. Do not loosen other denies.
- If the live grant row exists, remove only that role's `work.update` row with a single targeted delete/update. Do not copy `catalog/content_library.sqlite`. Do not shutil.copy2, vacuum, or backup that file. Do not write `catalog/backups`. Do not rewrite the database file. If the live grant cannot be changed without copying that file, do not copy it: ship the seed/role fix, test on a temp database, and write the result as BLOCKED_DISK for the live row only.

## Tests

Use a tiny temporary sqlite, or permission tables loaded into a database that is not the live content library. Never copy `catalog/content_library.sqlite`.

Prove, with a Head Chef principal created in that temp database (not a live login):

- the principal can `recipe.read`
- the principal cannot pass the gate used by `set_opening_float_ops` and `count_petty_ops` (`work.update` denied, both calls refused)
- a different role that already had `work.update` still has it

Do not log in as the chef. Do not claim a human pass, PROVEN_COMPLETE, staff_ready, or commissioned.

py_compile Python you edit.

## Do not touch

- Do not read or write close VDC-470e741f-d889-437a-9a40-1ec9c083fb95.
- Do not set BETA_AUTH_MODE.
- Do not restart or reload Beta. Do not signal Beta pid 47590. Do not signal production pid 15975.
- Leave pid 63443 alone.
- Do not commit, push, merge, reset, stash, or clean.
- Do not put secrets or process command lines in any file.

## Done

Write `state/reliability/HARYANTO-PERM-RESULT-2026-10-04.md` with files changed, the role grant removed, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE, BLOCKED, or BLOCKED_DISK.

Stop when that result file is written.
