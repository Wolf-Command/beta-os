# Head Chef permission leak — result (4 Oct 2026)

## Status

**IMPLEMENTATION_DONE**

Live `org_role_permissions` row removed (1 row deleted). Seed/migration updated so re-apply does not restore `work.update` on Head Chef.

## Role grant removed

- **Role:** `ROLE-BZG-HEAD-CHEF`
- **Permission revoked:** `work.update`
- **Mechanism:** targeted `DELETE FROM org_role_permissions` where `role_id='ROLE-BZG-HEAD-CHEF'` and `permission_id` for `work.update`
- **Live evidence:** migration reported `had_grant_before: true`, `rows_deleted: 1`, `grant_after: false`

Head Chef retains recipe and non-cash work grants: `recipe.read`, `recipe.create`, `recipe.edit`, `recipe.cost.read`, `recipe.exceptions.read`, `ingredient.read`, `menu.price.read`, `supplier.product.read`, `work.read`, `work.create`, `work.complete`, `evidence.record.read`, `evidence.record.submit`, `approval.request`.

## Files changed

| File | Change |
|------|--------|
| `scripts/migrations/migrate_headchef1_20260929.py` | Removed `work.update` from `EXISTING_GRANTS`; added `work.update` to `DENY_ASSERT` |
| `scripts/migrations/migrate_headchef_revoke_work_update_20261004.py` | New migration — targeted live revoke, no catalog copy/backup |
| `scripts/tests/test_headchef_work_update_revoke_20261004.py` | New temp-sqlite test for deny/allow gates |
| `scripts/tests/test_headchef1_20260929.py` | Added `work.update` to expected DENY list |

## Tests

**Command:**

```bash
PYTHONPATH=scripts python3 scripts/tests/test_headchef_work_update_revoke_20261004.py
```

**Result:** pass=6 fail=0 · `RESULT: PASS`

Proved on temp database (not live login):

- Head Chef principal can `recipe.read`
- Head Chef cannot pass `set_opening_float_ops` gate (`work.update` denied, 403 forbidden)
- Head Chef cannot pass `count_petty_ops` gate (`work.update` denied, 403 forbidden)
- Captain role still has `work.update`

**py_compile:** all edited Python files compiled clean.

## What was not changed

- No email/person-id patches in `serve_beta.py` or `uma_ops_console.py`
- No second permission system; cash gates still use existing `work.update` check
- No changes to assignment `ASG-HARIYANTO-HEAD-CHEF-1` or scope `SCOPE-BZG-FB` (leak was role grant only)
- Other roles with `work.update` (e.g. `ROLE-BZG-CAPTAIN`, `ROLE-BZG-CASHIER`) unchanged
- Did not copy, vacuum, or backup `catalog/content_library.sqlite`
- Did not touch close `VDC-470e741f-d889-437a-9a40-1ec9c083fb95`
- Did not set `BETA_AUTH_MODE`, restart Beta, or signal production/Beta pids
- No commit, push, or git operations
