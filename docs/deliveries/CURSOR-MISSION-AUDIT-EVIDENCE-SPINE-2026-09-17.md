# CURSOR MISSION — Audit / Evidence Spine (Beta OS only)

**Date:** 2026-09-17 (WITA)  
**Author:** Grok (Peaches executor) — governance brief only; Cursor writes app code  
**Lane:** Mac Beta `/Users/wolfterminal/beta-os/` on **:8788** only  
**Branch:** `build/wolf-command-rebuild` (must be CLEAN before start)  
**Expected HEAD at kickoff:** `f829f0c feat(core): bind verified Cloudflare identity`  
**machineId:** `36d8fa4b-2d58-4983-b227-e5bfa5495e78`  
**Commit message (single):** `feat(core): add audit evidence spine`  
**Remote / Production:** **NO** push, **NO** `:8787`, **NO** wolf-system edits

---

## Authority / role split

| Who | May |
|-----|-----|
| Peaches / Grok | Mission + canon honesty doc under `docs/` only |
| **Cursor (this agent)** | All `scripts/core/*`, migrations, `serve_beta.py` `/api/core/audit`, tests, seed, backup, one commit |
| Peaches / Grok | Must **not** write application code |

Read first (canon):

- `docs/BUILD-READ-ME-FIRST.md`
- `docs/RULE-Local-Cursor-Build-Path-2026-09-17.md`
- `docs/RULE-Beta-Construction-Production-Sacred-2026-09-16.md`
- `docs/RULE-Software-First-Agent-Scarcity-2026-09-16.md`
- `docs/deliveries/CURSOR-MISSION-AUTHORITY-LIMITS-2026-09-17.md`
- `docs/deliveries/CURSOR-MISSION-REAL-AUTH-BINDING-2026-09-17.md`
- Prior slices: `scripts/core/{request_auth,identity,rbac,authority,scope,cf_access}.py`
- Existing `/api/core/*` handlers + authority/auth tests

Also write/update: `docs/canon/AUDIT-EVIDENCE-SPINE.md` (honesty table).

---

## Phase 0 — Preflight (STOP if any fail)

```bash
cd /Users/wolfterminal/beta-os
git status -sb                    # must be CLEAN on build/wolf-command-rebuild
git rev-parse HEAD                # expect f829f0c (or document drift + STOP for Peaches)
git log -1 --oneline
```

### Backup BEFORE any migrate

```bash
TS=$(TZ=Asia/Makassar date +%Y%m%d-%H%M%S)
# Discover live SQLite path from core (do not invent). Typical Content catalog:
#   /Users/wolfterminal/beta-os/catalog/content_library.sqlite
# If core uses a separate DB, backup THAT file (and catalog if shared).
DB_PATH="<resolved sqlite path>"
mkdir -p /Users/wolfterminal/beta-os/catalog/backups
cp -p "$DB_PATH" "/Users/wolfterminal/beta-os/catalog/backups/pre-audit-spine-${TS}.sqlite"
shasum -a 256 "/Users/wolfterminal/beta-os/catalog/backups/pre-audit-spine-${TS}.sqlite" \
  | tee "/Users/wolfterminal/beta-os/state/audit-spine-backup-${TS}.sha256"
```

Record backup path + SHA-256 in the build notes at end of this mission file (append a short "## Build record" section).

---

## Goal (bounded)

Append-only **Audit / Evidence Spine** for security-critical decisions on Beta Core:

1. Schema `core_audit_events` (structured columns; not opaque-blob-first)
2. Service `scripts/core/audit.py` (INSERT-only API)
3. Permission `audit.event.read` seeded **only** for Owner / ROLE-MATT (no admin UI)
4. Read API `GET /api/core/audit` RBAC-gated
5. **Five** integration points only (not every route)
6. Tests `tests/test_core_audit.py` (or established `scripts/tests` pattern from prior slices)
7. One clean commit; working tree CLEAN after

**Honesty:** Prefer append-only + service deny UPDATE/DELETE + optional simple row hash for tamper-*evidence*.  
**Do NOT** claim cryptographic / court-grade immutability unless a hash-chain is actually implemented **and** tested in this slice (default: **do not** implement hash-chain this slice).

---

## Schema — `core_audit_events` (append-only)

Use migration style already used by Core (follow prior Real Auth / Authority migrations). Prefer real columns over opaque JSON for security-critical meaning.

| Column | Type | Notes |
|--------|------|--------|
| `audit_event_id` | TEXT PK | UUID |
| `occurred_at` | TEXT NOT NULL | ISO UTC when decision/action happened |
| `recorded_at` | TEXT NOT NULL | ISO UTC when row inserted |
| `created_at` | TEXT NOT NULL | ISO UTC (= recorded_at ok if single clock) |
| `actor_type` | TEXT NOT NULL | CHECK IN (`'PERSON'`,`'SYSTEM'`) |
| `actor_person_id` | TEXT NULL | PERSON only; from verified identity path |
| `actor_auth_identity_id` | TEXT NULL | |
| `actor_assignment_id` | TEXT NULL | |
| `identity_assurance` | TEXT NULL | e.g. `cloudflare_access_verified` / `none` / existing assurance enum |
| `entity_id` | TEXT NULL | |
| `brand_id` | TEXT NULL | if useful for WHERE |
| `location_id` | TEXT NULL | |
| `department_id` | TEXT NULL | |
| `scope_id` | TEXT NULL | |
| `action` | TEXT NOT NULL | stable verb codes |
| `resource_type` | TEXT NULL | |
| `resource_id` | TEXT NULL | |
| `result` | TEXT NOT NULL | **closed set** below |
| `reason_code` | TEXT NULL | |
| `correlation_id` | TEXT NOT NULL | accept or mint UUID per request |
| `source` | TEXT NOT NULL | e.g. `request_auth`, `rbac`, `authority`, `content_planner` |
| `before_hash` | TEXT NULL | optional content/state hash — not JWT |
| `after_hash` | TEXT NULL | |
| `evidence_reference` | TEXT NULL | |
| `corrects_event_id` | TEXT NULL | FK-ish to prior `audit_event_id` for corrections |
| `metadata_json` | TEXT NULL | **allowlisted non-secret extras only**; size-capped (e.g. ≤4KiB); strip secrets |

### Result closed set (pick and lock)

```
ALLOWED | DENIED | SUCCEEDED | FAILED | ERROR
```

- Auth success → `SUCCEEDED` (or `ALLOWED` if you model auth as authorization — pick one and use consistently; prefer **`SUCCEEDED`** for verified auth resolution, **`DENIED`** for auth/RBAC/authority denials).
- Mutations after commit → `SUCCEEDED` / `FAILED` / `ERROR`.
- Never log `ALLOWED` when the decision was deny.

### Append-only enforcement

- Service layer: **no** `update_event` / `delete_event` (raise `NotImplementedError` or omit).
- Correction = **INSERT** new row with `corrects_event_id` set.
- Optional SQLite triggers denying UPDATE/DELETE on `core_audit_events` for defense-in-depth (ok).
- Do **not** add event bus / Decision Ledger / SIEM / AI scoring.

---

## Service — `scripts/core/audit.py`

Required surface:

- `record_event(...)` — **only INSERT**
- `get_event(audit_event_id)` / `list_events(**filters)` — filters: entity/scope/actor/action/result/time/correlation/source as natural
- `correct_event(prior_id, ...)` — INSERT correction referencing prior
- Refuse `update_event` / `delete_event`
- `strip_secrets` / never accept fields named like `jwt`, `password`, `cookie`, `api_key`, `authorization`, `token` (case-insensitive); scrub nested metadata
- `actor_type=SYSTEM` → reject if `actor_person_id` set
- `actor_type=PERSON` → `actor_person_id` **must** come from verified identity path (same as Real Auth: never from client subject headers)
- `correlation_id`: accept caller value or mint UUID
- Fail closed on validation errors (do not silently drop security events if possible; if write fails, surface ERROR without crashing the deny path — follow prior core logging patterns)

Wire through existing DB connection helpers used by `rbac` / `authority` / `request_auth`.

---

## Permission

Seed **`audit.event.read`** (or canon-aligned code if Core already has a naming scheme — match existing permission codes) **ONLY** for Owner / **ROLE-MATT**.

- Follow existing seed pattern from prior Core slices (permissions table / role grants).
- **No** audit admin UI.
- Non-Matt roles: no read.

---

## Read API

`GET /api/core/audit`

- RBAC: require `audit.event.read`
- Filters: entity (if scoped), time, action, result, correlation_id, source — keep small
- Never return raw secrets (already stripped at write)
- Paginate conservatively (limit/offset or cursor; default low limit)

---

## Integrations — SMALL set (exactly these five)

Instrument **after** verifying the live call sites in Real Auth / Authority / Content Machine code.

| # | When | actor_type | result | source (example) | Notes |
|---|------|------------|--------|------------------|-------|
| 1 | Successful verified auth resolution | PERSON | SUCCEEDED | `request_auth` | assurance e.g. `cloudflare_access_verified`; person_id from verified path |
| 2 | Failed protected auth (missing/invalid JWT) | SYSTEM (or anonymous SYSTEM) | DENIED | `request_auth` / `cf_access` | assurance `none`; **never** store JWT body |
| 3 | RBAC denial on one representative protected action | PERSON or SYSTEM as accurate | DENIED | `rbac` | e.g. permissions evaluate deny path |
| 4 | Authority denial on representative material check | PERSON | DENIED | `authority` | amount + no limit (match Authority Limits mission semantics) |
| 5 | One successful Content Machine **mutation** | PERSON | SUCCEEDED | `content_planner` | **Smallest real write that already exists** — prefer `POST /api/planner/save` **or** approve if that is the smallest proven write; audit **AFTER successful commit** |

Rules:

- Mutations: audit **after** successful DB commit.
- Denials: audit the decision as **DENIED** (never ALLOW when denied).
- Do **not** instrument-all-routes.

---

## Tests — Matt mandatory list

Create `tests/test_core_audit.py` (or mirror prior slice test path). Cover at least:

1. `record_event` inserts; row readable via `get_event` / `list_events`
2. UPDATE/DELETE refused (service raises / missing)
3. `correct_event` inserts new row with `corrects_event_id`
4. SYSTEM + `actor_person_id` rejected
5. PERSON without verified person_id rejected (no client header spoof)
6. Secret fields stripped / rejected (`jwt`, `password`, etc.)
7. `metadata_json` size cap / allowlist behavior
8. RBAC: Matt can `GET /api/core/audit`; non-Matt cannot
9. Integration smoke (unit or light API): auth success → event; auth fail → DENIED without JWT body
10. RBAC deny → DENIED event
11. Authority deny (amount + no limit) → DENIED event
12. Content mutation success → SUCCEEDED after commit
13. Append-only: direct SQL UPDATE/DELETE blocked if triggers added (optional but preferred)

Use the same test harness / `development_assertion` patterns as Real Auth / Authority tests. Do not weaken Real Auth.

---

## Explicit DO NOT

- Event bus, Decision Ledger, admin UI, SIEM, AI scoring
- Instrument-all-routes
- Peaches/Grok writing `serve_beta` / `scripts/core` app code (Cursor only)
- Production wolf-system / `:8787`
- Remote push
- Claiming court-grade crypto immutability without implemented+tested hash-chain
- Storing JWT / cookies / passwords / API keys in audit rows

---

## Done checklist

- [ ] Preflight CLEAN + HEAD noted
- [ ] Backup path + SHA-256 recorded
- [ ] Migration applied on Beta DB only
- [ ] `scripts/core/audit.py` + tests green
- [ ] Permission seeded Matt-only
- [ ] `GET /api/core/audit` gated
- [ ] Five integrations only
- [ ] `docs/canon/AUDIT-EVIDENCE-SPINE.md` honesty table updated to match reality
- [ ] One commit: `feat(core): add audit evidence spine`
- [ ] Working tree CLEAN; no remote

---

## Cursor launch prompt (sole brief)

Implement this file end-to-end on Beta OS. Verify live patterns for SQLite path, migrations, permission seed, Content Machine write endpoint, and `development_assertion` before coding. Stay on `build/wolf-command-rebuild`. Backup DB first. One commit. No prod.

---

## Build record (Cursor fills)

- Backup path:
- SHA-256:
- HEAD before:
- HEAD after:
- Tests run:
- Notes / drift:
