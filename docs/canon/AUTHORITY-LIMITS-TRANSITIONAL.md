# Authority Limits — Transitional (Beta)

**Status:** SCHEMA_BUILT + EVALUATOR TESTED on Beta. Access control NOT LIVE.

## Path

```
Person → active Assignment → Role → Permission (WHAT)
                              ↘ Scope (WHERE)
                              ↘ Authority Limit (HOW MUCH)
```

- **Permission / RBAC (009)** = WHAT  
- **Scope (008)** = WHERE  
- **Authority Limit (010)** = HOW MUCH / material conditions  
- Authority **never** creates Permission  
- **Real Cloudflare Auth** = NOT BUILT (`DEVELOPMENT_IDENTITY_ASSERTION` still spoofable)

## Backup (before migrate on live Beta SQLite)

| field | value |
|-------|-------|
| path | `/Users/wolfterminal/beta-os/backups/content_library-pre-authority-20260917-090852.sqlite` |
| SHA-256 | `8d694898da1dc13cff497f460fab1eb6a5d8435b3ee592e3cb28337c65dbd2fa` |

## Table

`org_authority_limits` — assignment- or role-scoped AMOUNT limits with currency, threshold, `LTE_INCLUSIVE`, effective dates, `active`/`inactive`.

Unique control (fail on conflict; no silent merge):

- assignment rows: `(assignment_id, permission_id, scope_id, limit_type, currency, effective_from)`
- role rows (assignment_id NULL): `(role_id, permission_id, scope_id, limit_type, currency, effective_from)`

**SEEDED LIVE AUTHORITY LIMITS = 0.** No invented IDR staff thresholds on the live Beta DB. Test fixtures only (temp sqlite).

Optional inactive catalog permission: `PERM-TEST-SPEND` / `test.spend.approve` — not granted to live roles.

## Evaluator

`core.authority.within_authority(person_id, permission_code, target_context, amount_context)`

Order (hard):

1. RBAC `evaluate` — if not allowed → `rbac_denied`
2. Active Assignment required
3. Valid Scope covering target (reuse `_scope_covers_target`)
4. Matching active Authority Limit (assignment match preferred over role; `scope_id` NULL = any validated scope)
5. Material conditions (missing / malformed / negative amount; currency mismatch; effective window)
6. `LTE_INCLUSIVE` threshold — equal allowed; above → `higher_approval_required`

**Conflict rule:** among matching active limits, use the **strictest** (lowest `threshold_value`). Do not average. Do not ask an LLM.

Honesty on every decision:

```
real_authentication / delegation / dual_approval / segregation_of_duties = NOT_BUILT
ai_decision = False
```

`within_authority_bool(...)` thin wrapper. RBAC remains permission-only (`authority_limits: NOT_BUILT` on rbac path).

## APIs (read/check only)

- `GET /api/core/authority/check` — within_authority decision
- `GET /api/core/me/authority-limits` — active limits visible for current person's assignments/roles

No write/admin UI routes.

## NOT BUILT

- Authority admin UI
- Delegation
- Dual approval
- Segregation of duties
- Real Cloudflare Access JWT authentication
- Access control LIVE

Locked ★ 17 Sep 2026 — `build/wolf-command-rebuild` only.
