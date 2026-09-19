# GROK PLAN — Wolf Completion Register + Progress Open Loops — 2026-09-19

## Mandate
Owner Autonomous Release (19 Sep 2026). First permanent deliverable before expanding lanes.

## Goal
Canonical **Completion Register** = deterministic read model/index of everything Wolf knows remains incomplete. Project summary as **Open Loops** on `/progress`. Reuse Core Work Items + existing evidence; do not invent a second task system.

## Non-goals
- No Production mutation
- No inventing business policy / float / authority / fake numbers
- No dumping hundreds of eng tasks on Matt
- Do not convert every review sentence into an item
- Do not chase SYSTEM %
- Preserve dirty WIP: `scripts/migrations/migrate_phase2_6_team_readiness.py`, `scripts/phase26_team.py`, `scripts/skills/__init__.py`, `scripts/wolf_intelligence.py`

## Design

### Storage
- Table `wolf_completion_items` in Beta `catalog/content_library.sqlite` (or thin view over work_items + register metadata)
- Prefer: register rows with optional `work_item_id` link — register is the Owner-facing index; Work Items remain the task primitive where a WI already exists
- No DELETE: resolve with `RESOLVED` + resolution_evidence + resolved_at

### Item fields (nullable when unknown — do not invent)
ID, DOMAIN, CAPABILITY, ENTITY/SITE/VENUE/BRAND, TYPE, TITLE, WHY_IT_MATTERS, STATE, BLOCKER_CLASS, OWNER_ROLE, DEPENDENCY, EVIDENCE, SOURCE, FIRST_SEEN, LAST_CHECKED, NEXT_ACTION, RESOLUTION_EVIDENCE, RESOLVED_AT

### States
OPEN | IN_PROGRESS | BLOCKED | WAITING_HUMAN | WAITING_EXTERNAL | VERIFYING | RESOLVED

### Blocker classes
NEEDS_MATT | NEEDS_STAFF | NEEDS_POLICY | NEEDS_EXTERNAL_ACCESS | NEEDS_ENGINEERING | NEEDS_EVIDENCE | NEEDS_COMMISSIONING | NEEDS_ADOPTION

### Auto-discovery (seed, deduped)
Read-only harvest into OPEN items from authorised evidence only:
1. Model C evidence ledger rows ABSENT/SPECIFIED/BUILT (not READY) as capability debt — map CAP-ID
2. Model E adoption REQUIRED AUs NOT STARTED / COMMISSIONING
3. Factory blocked/parked lanes + known WAKE/blockers
4. Build claims waiting human (e.g. Devi commissioning)
5. Known defects already documented (ENDED scope resurrection, etc.)
6. Recent Grok review FAIL/open findings that are still material (bounded: last N review docs with explicit OPEN findings — do not spam)
7. Uma/BZG: opening float missing, closer missing, cutover_at unset (as NEEDS_POLICY / NEEDS_COMMISSIONING — not fake NEEDS_MATT unless Owner-only)

Dedup key: (CAPABILITY or TYPE+TITLE normalized, ENTITY). Upsert last_checked; never wipe history.

### Closure rule
OPEN → RESOLVED only with `resolution_evidence` pointing at real proof (commit, prove script, commissioning claim). Maturity change alone does not close.

### API / read model
- `scripts/core/completion_register.py`: ensure_schema, upsert, list_open, summary_for_owner, mark_resolved
- `GET` projection used by progress_read_model (no new public unauth surface if progress already gated)

### Progress Open Loops (Owner)
On `/progress` Empire (and drill-downs):
- Section **Open Loops** summarizing: total open, in progress, blocked, Needs Matt, Needs Staff, Needs Policy, Needs External, commissioning/adoption debt, oldest material items (top 5–10), recently resolved (top 5)
- Needs Matt = blocker_class NEEDS_MATT only
- Drill filters by Empire / GGV / AMG / BZG / Core / Intelligence / Integrations / Sale / Factory
- Numbers computed at read time from register — never hard-coded in HTML

### Tests
- Schema + upsert + dedup
- Summary counts
- Resolve requires evidence
- Seed from a tiny fixture ledger slice does not invent Matt blockers incorrectly
- Progress payload includes open_loops with required keys
- Deployed-route: GET /progress still 200 and contains Open Loops marker after soft apply

### Success
1. Register exists and is seeded from real evidence (non-empty OPEN set)
2. /progress shows Open Loops summary (no eng dump)
3. Factory claim updated; next autonomous lane eligible after DONE
4. SYSTEM % unchanged

## Factory slice
`BF-completion-register-20260919`
