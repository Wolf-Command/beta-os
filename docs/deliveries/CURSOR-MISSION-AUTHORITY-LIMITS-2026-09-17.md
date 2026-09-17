# CURSOR MISSION — WOLF CORE AUTHORITY LIMITS

**Grok planned:** YES (reconfirmed 17 Sep 2026 against HEAD `39ef72e`)
**Peaches:** Governor only — do not let Peaches Shell-write application code.
**Implementer:** Cursor Local Agent on Wolfs-Mac-Studio
**Repo:** `/Users/wolfterminal/beta-os/`
**Branch:** `build/wolf-command-rebuild` (must start CLEAN)
**Commit message when done:** `feat(core): add deterministic authority limits`
**No remote. No merge to main. No Production. No admin UI. No delegation. No dual approval. No SoD. No real auth.**

## Preflight (Cursor must print evidence)

```
hostname; whoami; pwd; git branch --show-current; git rev-parse HEAD; git status --short
```

Must match: Wolfs-Mac-Studio.local / wolfterminal / `/Users/wolfterminal/beta-os` / `build/wolf-command-rebuild` / CLEAN.

Read before coding:
1. `docs/BUILD-READ-ME-FIRST.md`
2. `docs/RULE-Software-First-Agent-Scarcity-2026-09-16.md`
3. `docs/RULE-Beta-Construction-Production-Sacred-2026-09-16.md`
4. `docs/RULE-Local-Cursor-Build-Path-2026-09-17.md`
5. `docs/canon/RBAC-PERMISSIONS-TRANSITIONAL.md`
6. `docs/canon/ASSIGNMENT-SCOPE-TRANSITIONAL.md`
7. Mirror patterns in `scripts/core/rbac.py`, `scripts/migrations/009_*`, `migrate_rbac_permissions.py`, `test_rbac_permissions.py`, `serve_beta.py` ensure_schema hooks.

## Concepts (do not blur)

- Permission = WHAT
- Scope = WHERE
- Authority Limit = HOW MUCH / material conditions
- Authority must **never** create Permission
- No opaque JSON rules engine
- No LLM / prompt in decision path

## Schema — `org_authority_limits`

Migration **`010_authority_limits.sql`** + **`migrate_authority_limits.py`** (idempotent).

Columns (minimum):

| column | notes |
|--------|--------|
| authority_limit_id | TEXT PK |
| role_id | TEXT NULL FK org_roles |
| assignment_id | TEXT NULL FK org_assignments |
| permission_id | TEXT NOT NULL FK org_permissions |
| scope_id | TEXT NULL FK org_scopes |
| limit_type | TEXT NOT NULL — start with `AMOUNT` only |
| currency | TEXT NULL (ISO, e.g. `IDR`) — required when limit_type=AMOUNT |
| threshold_value | REAL NULL — required when limit_type=AMOUNT; store as number |
| comparison_rule | TEXT NOT NULL — `LTE_INCLUSIVE` (equal counts as within) |
| effective_from | TEXT NOT NULL ISO |
| effective_to | TEXT NULL |
| status | TEXT NOT NULL — `active` / `inactive` |
| created_at / updated_at | TEXT NOT NULL |

Constraints / discipline:

- CHECK: at least one of role_id or assignment_id is non-null (prefer assignment-specific overrides over role; evaluator resolves assignment match first, then role match).
- UNIQUE control for duplicates: unique on (assignment_id, permission_id, scope_id, limit_type, currency, effective_from) where assignment_id not null; and (role_id, permission_id, scope_id, limit_type, currency, effective_from) where role_id not null and assignment_id null. Fail deterministic on conflict; do not silently merge.
- Same beta/wolf-system path guards as rbac.py (refuse production DB paths).

**SEEDED LIVE AUTHORITY LIMITS = 0.** Do not invent live IDR staff thresholds. Test fixtures only (in tests / temp DB), never in production seed for real people.

Optional test-only permission for fixtures (ok to seed in migration as inactive catalog entry only if needed):
- `PERM-TEST-SPEND` / code `test.spend.approve` — **not** granted to live roles in migrate seed. Tests grant via fixture DB.

Or tests may insert fixture permission + role grant + authority limit into a temp sqlite. Prefer temp DB fixtures over polluting live role grants.

## Module — `scripts/core/authority.py`

`within_authority(person_id, permission_code, target_context, amount_context) -> dict`

`amount_context` shape (deterministic dict, not free JSON rules):
```
{"amount": <number|None>, "currency": <str|None>, "at": <ISO datetime optional>}
```

Order (hard):

1. RBAC: call `core.rbac.evaluate` / `can` — if not allowed → DENY (`rbac_denied`)
2. Active Assignment for person — if none → DENY
3. Valid Scope covering target_context — if not → DENY (reuse `_scope_covers_target` / scope resolver; do not reimplement inheritance differently)
4. Matching active Authority Limit for (assignment or role) + permission + scope (scope_id null = applies to any scope already validated in step 3) + effective dates → if none → DENY with reason `higher_approval_required` (or `no_matching_authority_limit`)
5. Material conditions:
   - malformed / non-numeric amount → DENY
   - negative amount → DENY
   - missing amount when limit_type=AMOUNT → DENY
   - currency mismatch → DENY
   - expired (effective_to < at) or not yet effective → DENY
6. Threshold with `LTE_INCLUSIVE`:
   - amount < threshold → ALLOW
   - amount == threshold → ALLOW
   - amount > threshold → DENY `higher_approval_required`

Conflict rule: if multiple matching limits apply, use the **strictest** (lowest threshold_value) among active matches. Document this. Do not average. Do not ask LLM.

Honesty labels in every decision dict:
```
"real_authentication": "NOT_BUILT",
"delegation": "NOT_BUILT",
"dual_approval": "NOT_BUILT",
"segregation_of_duties": "NOT_BUILT",
"ai_decision": False
```

Also expose `within_authority_bool(...)` thin wrapper.

Update `core.rbac.evaluate` honesty field `authority_limits` from `"NOT_BUILT"` to note authority is separate module (e.g. `"SEE_core.authority"` or keep NOT_BUILT on rbac path and only claim BUILT on within_authority — preferred: rbac stays permission-only; authority is separate).

## APIs (minimal read/check only)

In `serve_beta.py`:

- Wire `migrate_authority_limits` into `ensure_schema` (same pattern as RBAC).
- `GET /api/core/authority/check` — query params or JSON body for person (from DEVELOPMENT_IDENTITY_ASSERTION), permission_code, target fields, amount, currency. Returns within_authority decision. Read-only check.
- Optional `GET /api/core/me/authority-limits` — list active limits visible for current person's assignments/roles (no private HR). Minimal fields.

No write/admin UI routes.

## Tests — `scripts/tests/test_authority_limits.py`

Mandatory cases (Matt list). Use temp sqlite + run migrations. Include:

- Permission required (RBAC fail → deny)
- Scope required
- active Assignment required
- wrong Entity denied
- wrong Scope denied
- expired Authority denied
- below / exact / above threshold (LTE_INCLUSIVE)
- negative / malformed / missing amount
- currency mismatch
- Authority without Permission denied
- Permission without Authority denied when calling within_authority (no matching limit)
- multiple Assignments
- conflicting limits → strictest wins deterministically
- duplicate limits controlled (constraint / idempotent migrate)
- email identity alone grants nothing
- no AI in decision path (grep source: no openai/anthropic/llm calls in authority.py)
- Content Machine compatibility (legacy permissions table untouched; content flows still work)
- migration idempotent
- no Production path references that write/open prod DBs

## Docs / build state

- Add `docs/canon/AUTHORITY-LIMITS-TRANSITIONAL.md` (honesty + model + NOT BUILT list).
- Update `docs/canon/build-dashboard/Master_Build.csv` MB-003 next action honestly:
  - Authority Model = BUILT
  - Authority Evaluator = TESTED
  - RBAC integration = TESTED
  - Authority admin UI = NOT BUILT
  - Delegation / Dual Approval / SoD / Real Auth = NOT BUILT
  - Access Control = NOT LIVE

## Backup (before migration on live Beta DB)

```
# Cursor must do this before applying migrate to content_library.sqlite
cp <beta sqlite> backups/content_library-pre-authority-YYYYMMDD-HHMMSS.sqlite
shasum -a 256 <backup>
```

Record path + SHA-256 in the transitional doc or test output. Never touch Production DBs.

## Done criteria

1. All tests pass
2. Working tree only Authority Limits related files
3. One commit: `feat(core): add deterministic authority limits`
4. Working tree CLEAN after commit
5. Print: migration name, backup path+sha, test summary, seeded live count (=0), file list

STOP. Do not build anything else.
