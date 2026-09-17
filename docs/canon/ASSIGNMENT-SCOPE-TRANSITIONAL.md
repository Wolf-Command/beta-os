# Assignment Scope — Transitional (Beta)

**Status:** SCHEMA_BUILT + TESTED on Beta. Access control NOT LIVE.

## What Scope answers

**WHERE** does this Assignment apply?

It does **not** answer WHAT the person can do (RBAC/Permissions) or how much authority they have (Authority Limits).

## Model

```
Person → active Assignment → Scope(s) → Scope Target(s)
                         ↘ Position → Role
```

Scopes attach to **Assignments**, never directly to Person.

Tables:

- `org_scopes` — scope_id, scope_type, display_name, status, timestamps
- `org_scope_targets` — (scope_id, target_type, target_id) relational; no opaque JSON rules
- `org_assignment_scopes` — Assignment↔Scope link with start/end history

Supported `scope_type` / `target_type` (extensible): `entity`, `brand`, `location`, `department`. Client modelling deferred.

## Inheritance intent (structural only)

| Target | Structural cover | Must NOT auto-include |
|--------|------------------|------------------------|
| Entity | That entity's brands, locations, departments (listed for later eval) | Other legal entities |
| Brand | That brand only | Sibling brands |
| Location | That location only | Unrelated locations |
| Department | That department only | Other departments |

`resolve_effective_scope_context` sets `inheritance_not_permission=True` and `permission_decision=NOT_BUILT`.

Ending an Assignment does **not** delete Scope definitions or historical `org_assignment_scopes` rows.

## Conservative Beta seed

- `SCOPE-GGV-ALL` → entity `ENT-GGV`
- `SCOPE-GGV-CONTENT` → department `DEPT-GGV-CONTENT`
- Matt owner assignment → both scopes
- Amanda / Haikal / Misa content assignments → `SCOPE-GGV-CONTENT`

No invented AMG/BZG staff assignment scopes.

## NOT BUILT

- Real Cloudflare Access JWT authentication (still `DEVELOPMENT_IDENTITY_ASSERTION`)
- Access control LIVE

## Related (built elsewhere)

- RBAC / Permissions — see `RBAC-PERMISSIONS-TRANSITIONAL.md`
- Authority Limits — see `AUTHORITY-LIMITS-TRANSITIONAL.md` (HOW MUCH; seeded live = 0)

## APIs (read-only Beta)

- `GET /api/core/scopes`
- `GET /api/core/scopes/{id}`
- `GET /api/core/assignments/{id}/scopes`
- `GET /api/core/me/scopes` — reports `identity_assurance` development assertion; `real_authentication=false`

Locked ★ 17 Sep 2026 — Beta `build/wolf-command-rebuild` only.
