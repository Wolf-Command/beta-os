# NOTE — Haikal seated on Creative Director — 2026-09-24

**Class:** Owner-settled Assignment seat change (People ≠ Roles).  
**Executor:** Peaches cheap/local (no Cursor launch).  
**Owner answer:** Seat Haikal on Creative Director (`ROLE-GGV-CREATIVE-DIRECTOR`).  
**When:** 2026-09-24 17:34 WITA · soft head `f3ab8f7` preserved · Beta `:8788` · Prod `:8787` untouched.  
**DB:** `catalog/content_library.sqlite` (transaction-safe).

## Before

| Row | Value |
| --- | --- |
| Person | `PERS-HAIKAL` ACTIVE |
| Assignment | `ASG-HAIKAL-VE-1` → `POS-VIDEO-EDITOR-1` → `ROLE-GGV-EDIT` (Video Editor) ACTIVE `is_primary=1` |
| Creative Director position | **none** (`ROLE-GGV-CREATIVE-DIRECTOR` existed; zero `org_positions`) |
| Scopes on VE | `SCOPE-GGV-CONTENT`, `SCOPE-GGV-HABITAT-LEAD`, `SCOPE-CRM-HABITAT-LEAD`, `SCOPE-GGV-CONTENT-LIBRARY` ACTIVE |

## After (mutated)

| Action | Id / result |
| --- | --- |
| Created position | `POS-GGV-CREATIVE-DIRECTOR-1` · role `ROLE-GGV-CREATIVE-DIRECTOR` · entity `ENT-GGV` · dept `DEPT-GGV-CONTENT` · label **Creative Director #1** · ACTIVE · fte 1.0 · ts `2026-09-24T17:34:12+08:00` |
| Ended VE assignment | `ASG-HAIKAL-VE-1` → status **ENDED**, `end_at` + `updated_at` = now, `is_primary=0` (**history preserved**, not deleted) |
| Ended VE scopes | same four scopes → **ENDED** with `end_at` now |
| Created CD assignment | `ASG-HAIKAL-CD-1` · `PERS-HAIKAL` → `POS-GGV-CREATIVE-DIRECTOR-1` · ACTIVE · `is_primary=1` · `start_at` now · `end_at` NULL |
| Reattached scopes | same four scopes ACTIVE on `ASG-HAIKAL-CD-1` (seat continuity; not a broad refactor) |

## Did NOT

- Invent `ROLE-CONTENT-DIRECTOR` or `ROLE-HAIKAL`
- Rename / touch `ROLE-CONTENT-MGMT` (Amanda `ASG-AMANDA-CM-1` unchanged)
- Kill Cursor pid 45807 / launch a new pack
- Touch prod `:8787`
- Set `staff_ready` / commissioned / telegram_retired
- Copy `org_role_permissions` onto Creative Director (see gap)

## Permissions gap (documented — not copied)

`ROLE-GGV-CREATIVE-DIRECTOR` already had **2** ALLOW rows (`PERM-APPROVAL-DECIDE`, `PERM-CONTENT-HABITAT-APPROVE`) — **not zero**, so no copy from `ROLE-GGV-EDIT` (12) / `ROLE-CONTENT-MGMT` (27) this pass.

**People ≠ Roles debt:** Content Engine ACL on deployed Beta is still largely **email / person-subject** based. Seat change alone does not complete Assignment→Role authz. Prefer document; fold into CE repair verify — do not invent ROLE perms from this NOTE alone.

## Verify SELECTs (post-commit)

```
ASG-HAIKAL-CD-1  PERS-HAIKAL  POS-GGV-CREATIVE-DIRECTOR-1  ACTIVE  is_primary=1
ASG-HAIKAL-VE-1  PERS-HAIKAL  POS-VIDEO-EDITOR-1           ENDED   is_primary=0  end_at=2026-09-24T17:34:12+08:00
POS-GGV-CREATIVE-DIRECTOR-1  ROLE-GGV-CREATIVE-DIRECTOR  ENT-GGV  DEPT-GGV-CONTENT  Creative Director #1  ACTIVE  1.0
```

## Related

- RULE: `docs/RULE-Wolf-People-Are-Not-Roles-2026-09-24.md` (ADDENDUM Owner settled)
- CR: `state/completion-register/wolf-people-are-not-roles-20260924.json` (`seat_resolved=true`)

## Seed migrate sync (stickiness)

`scripts/serve_beta.py` re-runs idempotent org migrates on start. Initial seat end was briefly revived by `migrate_role_position_assignment.py` seeding `ASG-HAIKAL-VE-1` ACTIVE.

Updated (same pass, not a new pack):
- `scripts/migrations/migrate_role_position_assignment.py` — seeds `ROLE-GGV-CREATIVE-DIRECTOR`, `POS-GGV-CREATIVE-DIRECTOR-1`, `ASG-HAIKAL-CD-1` ACTIVE; `ASG-HAIKAL-VE-1` ENDED `end_at=2026-09-24T17:34:12+08:00`
- `scripts/migrations/migrate_assignment_scope.py` — VE `SCOPE-GGV-CONTENT` ENDED; CD gets ACTIVE `SCOPE-GGV-CONTENT`

Re-ran both migrates: seat stayed ENDED/ACTIVE as intended. Cursor 45807 not interrupted.

