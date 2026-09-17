# RBAC / Permissions — Transitional (Beta)

**Status:** SCHEMA_BUILT + TESTED on Beta. Access control NOT LIVE.

## Path

```
Person → Auth Identity → active Assignment → Position → Role → Scope → Permission
```

- **Scope (008)** = WHERE  
- **RBAC (009)** = WHAT  
- **Authority Limits** = BUILT+TESTED in `core.authority` (separate; seeded live = 0) — see `AUTHORITY-LIMITS-TRANSITIONAL.md`  
- **Real Cloudflare Auth** = BUILT+TESTED (fixtures); LIVE pending AUD — see `REAL-AUTH-BINDING-TRANSITIONAL.md`

## Tables

- `org_permissions` — canonical codes (`content.plan.read`, …)
- `org_role_permissions` — Role → Permission ALLOW grants (deny by default)
- `org_permission_legacy_map` — `can_*` → canonical (TRANSITIONAL)
- Legacy `permissions` (email subject) rows **kept** as TRANSITIONAL fallback when no Person exists

## Evaluator

`core.rbac.can(person_id, permission_code, target_context)` / `evaluate(...)`

Deterministic software only. No AI/LLM. Explains Person / Assignment / Role / Scope / result.

## Content Machine adapter

`wolf_intelligence.has_permission(email, …)` resolves email → Person then calls RBAC with default Content target `{entity_id: ENT-GGV, department_id: DEPT-GGV-CONTENT}`. Legacy email rows used only if Person missing.

## Vertical slice API protection

- `GET /api/core/entities` → `organisation.entity.read`
- `GET /api/core/persons` → `organisation.person.read`
- `GET /api/core/me/permissions` — effective codes + honesty labels

UI visibility is not security. Server enforcement mandatory.

## Known blocker

Identity spoofing via `X-Wolf-Subject` still works on Beta until real CF JWT auth.

Locked ★ 17 Sep 2026 — `build/wolf-command-rebuild` only.
