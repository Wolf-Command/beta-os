# CURSOR MISSION — Wolf Core Work Items (Beta OS only)

**Date:** 2026-09-17 (WITA)  
**Grok planned:** YES against HEAD `8fd0b2d`  
**Peaches:** Governor only — no application coding by Peaches Shell.  
**Implementer:** Cursor Local Agent on Wolfs-Mac-Studio  
**Repo:** `/Users/wolfterminal/beta-os/`  
**Branch:** `build/wolf-command-rebuild` (start CLEAN)  
**Commit:** `feat(core): add work item task primitive`  
**No remote. No main merge. No Production. No Kanban UI. No scheduler. No notifications. No approval engine. No live Authority Limits seed.**

---

## Naming law (avoid collision)

| Concept | Canonical name | NOT |
|---------|----------------|-----|
| Person occupies Position over time | `org_assignments` / Organisation Assignment | never call this a “task” |
| Something must be done | **Work Item** / table `core_work_items` | do **not** name table `tasks` or `assignments` |
| Permission verb / audit verb | `action` (existing) | fine elsewhere; Work Item uses `work_type` + status transitions |
| Existing Content evidence rows | `evidence_items` (legacy Content) | Work Item uses **references only** (`completion_evidence_reference`); do not reinvent Evidence File Store |

API prefix: `/api/core/work-items`  
Service: `scripts/core/work_items.py`  
Permissions: `work.read` | `work.create` | `work.update` | `work.assign` | `work.complete` | `work.verify`

---

## Preflight

```bash
cd /Users/wolfterminal/beta-os
git status -sb   # CLEAN on build/wolf-command-rebuild
git rev-parse HEAD  # expect 8fd0b2d (or later docs-only commits — document drift)
```

### Backup BEFORE migrate

```bash
TS=$(TZ=Asia/Makassar date +%Y%m%d-%H%M%S)
DB=catalog/content_library.sqlite
mkdir -p catalog/backups state
cp -p "$DB" "catalog/backups/pre-work-items-${TS}.sqlite"
shasum -a 256 "catalog/backups/pre-work-items-${TS}.sqlite" | tee "state/work-items-backup-${TS}.sha256"
```

Append path+SHA to `## Build record` at end of this mission when done.

---

## ★ TEST AUDIT POLLUTION (mandatory first fix)

### What the existing 47 `core_audit_events` rows are

**PROBLEM FOUND.** They are **not** mysterious production ops. Provenance on live Beta DB:

| source | action | result | ~n | meaning |
|--------|--------|--------|----|---------|
| `request_auth` | `auth.resolve` | SUCCEEDED | ~24 | mostly `auth_mode=development_assertion` from tests |
| `cf_access` / `request_auth` | `auth.resolve` | DENIED | ~10 | missing/misconfigured JWT tests |
| `authority` | `authority.check` | DENIED | 5 | authority deny integration tests |
| `rbac` | `rbac.evaluate` | DENIED | 5 | permission deny tests |
| `content_planner` | `content_planner.save` | SUCCEEDED | 3 | planner save tests (also created Draft slots on live) |

Root cause: `scripts/tests/test_core_audit.py` HTTP section sets `audit.CATALOG_DB = LIVE_DB` and asserts counts on live `content_library.sqlite`.

### Rules for this slice

1. **Do NOT DELETE** the 47 live audit events. Append-only evidence. Document in `docs/canon/WORK-ITEMS.md` + honesty note.
2. **Fix isolation** in `test_core_audit.py` AND write all new Work Item tests against a **temp DB copy only**. Point `audit.CATALOG_DB`, work_items DB, identity/rbac/authority catalog paths at the temp file for HTTP server tests. Never write new test events to live.
3. If you want a governed cleanup of the 47 later: **STOP and recommend** a separate Matt-approved migration — not this commit.
4. Live seed for Work Items: **0** rows (empty table).

Also harden `core.audit.safe_record` / test helpers so accidental live writes from tests fail closed when `WOLF_TEST_MODE=1` or when CATALOG_DB is unset and process is under `scripts/tests/` — prefer explicit temp wiring over magic.

---

## Work Item model

Table `core_work_items`:

| column | notes |
|--------|-------|
| `work_item_id` TEXT PK | e.g. `WI-…` uuid |
| `title` TEXT NOT NULL | |
| `description` TEXT NULL | instructions |
| `work_type` TEXT NOT NULL | closed set starter: `GENERAL`, `FOLLOW_UP`, `EXCEPTION`, `MAINTENANCE`, `APPROVAL_REQUIRED`, `AUDIT_FINDING`, `CONTENT`, `SYSTEM` |
| `status` TEXT NOT NULL | see state machine |
| `priority` INTEGER NOT NULL DEFAULT 3 | 1=highest … 5=lowest (supports future “3 needle movers”; no ranking engine now) |
| `owning_entity_id` TEXT NOT NULL | FK-ish to `org_entities` — **scope boundary** |
| `source_type` TEXT NOT NULL | `HUMAN`, `SYSTEM`, `AUDIT`, `ROUTINE`, `RECOMMENDATION_ACCEPTED`, `EXTERNAL` |
| `source_id` TEXT NULL | opaque reference |
| `created_by_actor_type` TEXT NOT NULL | `PERSON` \| `SYSTEM` |
| `created_by_person_id` TEXT NULL | required iff PERSON; forbidden for SYSTEM |
| `owner_person_id` TEXT NULL | one accountable owner |
| `owner_org_assignment_id` TEXT NULL | optional link to **org** assignment (seat), NOT “task assignment” |
| `due_at` TEXT NULL | ISO UTC |
| `started_at` TEXT NULL | |
| `completed_at` TEXT NULL | set when entering COMPLETED (claim) |
| `verified_at` TEXT NULL | set when entering VERIFIED |
| `outcome` TEXT NULL | short result text |
| `completion_evidence_reference` TEXT NULL | hook only — no file store |
| `parent_work_item_id` TEXT NULL | self-FK optional |
| `created_at` / `updated_at` TEXT NOT NULL | |

Indexes: entity, owner_person, status, due_at, parent.

### CLAIMED ≠ VERIFIED (chosen design)

Statuses (closed set):

`OPEN` → `IN_PROGRESS` → `BLOCKED` → `COMPLETED` → `VERIFIED`  
also: any non-terminal → `CANCELLED`  
`BLOCKED` → `IN_PROGRESS`  
`VERIFIED` and `CANCELLED` are terminal.

- **COMPLETED** = completion **claimed** (requires `work.complete`). Does **not** mean Wolf verified reality.
- **VERIFIED** = separate step (requires `work.verify`). Cannot skip COMPLETED → VERIFIED from OPEN.
- Client cannot set `status=VERIFIED` via raw update — only `verify_work_item()` transition.
- Completing does **not** require evidence_reference this slice (optional). If provided, store reference only.

Illegal transitions → 400 with reason; tested.

### Ownership

- Prefer single `owner_person_id`.
- `owner_org_assignment_id` optional; if set, must belong to that person and be ACTIVE (validate against `org_assignments`).
- `work.assign` required to change owner.
- SYSTEM-created items: `created_by_actor_type=SYSTEM`, `created_by_person_id` NULL — never masquerade as Person.

### Provenance

Preserve `source_type` / `source_id` / creator actor forever (immutable after create except via correction policy — this slice: **immutable provenance fields**).

AI recommendations: if ever created later, must use `source_type=RECOMMENDATION_ACCEPTED` only after human accept — **out of scope** to auto-create from LLM now. No LLM in this slice.

---

## Permissions (conservative)

Seed codes ACTIVE; grant **ROLE-MATT only** for all six:

`work.read`, `work.create`, `work.update`, `work.assign`, `work.complete`, `work.verify`

Do not invent staff grants. Entity/scope still enforced in service even for Matt (list filters by visible entities from Assignment scopes — Matt with SCOPE-GGV-ALL sees GGV; cannot see fabricated ENT-AMG row unless scope covers).

---

## Service `scripts/core/work_items.py`

- `create_work_item(...)` — verified identity for PERSON creator
- `get_work_item` / `list_work_items(person_id, filters)` — RBAC + entity scope
- `transition_status` / helpers: `start`, `block`, `claim_complete`, `verify`, `cancel`
- `reassign_owner`
- Refuse forged `created_by_person_id` / `owner_person_id` from client without matching verified identity + permission
- No DELETE of work items (cancel instead). History preserved.

### Audit integration (`core.audit.safe_record`)

Emit on: create, owner change, start, block, claim_complete, verify, cancel.  
Actor from verified identity / SYSTEM rules. Never client-spoofed person. Never store JWT/secrets.

---

## HTTP API (`serve_beta.py`)

| method | path | perm |
|--------|------|------|
| GET | `/api/core/work-items` | work.read |
| GET | `/api/core/work-items/{id}` | work.read |
| POST | `/api/core/work-items` | work.create |
| PATCH | `/api/core/work-items/{id}` | work.update (title/description/priority/due only — **not** status/owner/provenance) |
| POST | `/api/core/work-items/{id}/assign` | work.assign |
| POST | `/api/core/work-items/{id}/start` | work.update |
| POST | `/api/core/work-items/{id}/block` | work.update |
| POST | `/api/core/work-items/{id}/complete` | work.complete |
| POST | `/api/core/work-items/{id}/verify` | work.verify |
| POST | `/api/core/work-items/{id}/cancel` | work.update |

All fail-closed via `request_auth`. No UI.

---

## Migration

`scripts/migrations/012_work_items.sql` + `migrate_work_items.py`  
Idempotent. Seed permissions + ROLE-MATT grants. **0** live work items.

---

## Docs

Update/create `docs/canon/WORK-ITEMS.md` honesty table (BUILT/TESTED/NOT BUILT).  
Document the 47-event pollution + isolation fix + no silent delete.

---

## Tests — `scripts/tests/test_core_work_items.py`

Temp DB only. Cover Matt’s list: scoped visibility, wrong entity/scope deny, inactive assignment, permissions, owner model, illegal transitions, COMPLETED≠VERIFIED, audits for create/assign/complete/cancel, forged actor blocked, SYSTEM create provenance, secrets not stored, migration idempotent, Content Machine still loads (smoke import serve_beta), Production untouched.

Also **patch** `test_core_audit.py` HTTP section off LIVE_DB (prove with a check that live audit count does not increase during that test run).

---

## Explicit DO NOT

Project UI, Kanban, recurring scheduler, notifications, approval/SLA/escalation engines, daily-3 algorithm, AI task manager, staff scoring, Evidence File Store, Event Bus, deleting the 47 audit rows, seeding live Authority Limits, touching `:8787` / wolf-system.

---

## Build record

**Implementer:** Cursor Local Agent on Wolfs-Mac-Studio  
**HEAD start:** `f59b0bb` (`docs: Grok plan for core work items`)  
**Commit message:** `feat(core): add work item task primitive` (see `git log -1` on `build/wolf-command-rebuild`)  
**Decision served:** 2026-09-17 Local Cursor Build Path (LOCKED ★ Matthew) + approved CURSOR-MISSION-WORK-ITEMS-2026-09-17 (extends started Wolf Core rebuild)

### Backup (before migrate)

- Path: `catalog/backups/pre-work-items-20260917-102806.sqlite`
- SHA-256: `f149800daa17e3a1469ef0787cf98fb61488089d5bfdf4b1e30d70d2d1e80ec3`
- Record: `state/work-items-backup-20260917-102806.sha256`

### Evidence

- Live `core_work_items` count: **0**
- Live `core_audit_events` count: **47** (unchanged; no silent delete)
- `test_core_work_items.py`: SUMMARY pass=54 fail=0
- `test_core_audit.py` (off LIVE_DB): SUMMARY pass=45 fail=0
- Canon honesty: `docs/canon/WORK-ITEMS.md`
- No remote. No Production. No Kanban/UI/scheduler.
