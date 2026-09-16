# WOLF PHASE 1 BUILD REPORT — Content Intelligence
**Generated:** 2026-09-15 07:12:26 WITA  
**Scope:** `/Users/wolfterminal/beta-os/` (+ `/tmp/` reports)  
**Port policy:** :8788 beta only — :8787 wolf **untouched**

---

## A. Pre-flight verification
- CWD/root confirmed: `/Users/wolfterminal/beta-os`
- Before changes: :8788 = `serve_beta.py` (PID 81507); :8787 = wolf `serve.py` (PID 3758)
- After LaunchAgent restart: :8788 = new beta PID; **PID 3758 still alive**
- Current listeners:
```
COMMAND  PID         USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
Python  1862 wolfterminal    3u  IPv4 0xc483a668531b26ed      0t0  TCP 127.0.0.1:8788 (LISTEN)
Python  3758 wolfterminal    3u  IPv4 0x36047528d63f3bd9      0t0  TCP 127.0.0.1:8787 (LISTEN)
```
- Wolf process: `3758 /opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python /Users/wolfterminal/.openclaw/workspace/wolf-system/dashboards/serve.py 8787`

## B. Backups
- `catalog/backups/content-2.0.html.bak-phase1-20260915-070530`
- `catalog/backups/content_library.sqlite.bak-phase1-20260915-070530`
- `archive/baks/content-2.0.html.bak-phase1-20260915-070530`
- `archive/baks/serve_beta.py.bak-phase1-20260915-070530`
- Pre-migration dump: `/tmp/phase1-pre-migration.txt`

## C. Schema migration (Phase 1A)
- Script: `scripts/migrations/001_phase1_intelligence.sql` + `scripts/migrations/migrate_phase1.py`
- Additive `CREATE TABLE IF NOT EXISTS` + indexes (idempotent)
- Tables: brands, permissions, memory_items, evidence_items, content_plans, plan_revisions, content_cards, card_revisions, skill_runs
- `PRAGMA foreign_keys=ON` enabled in `serve_beta.db_connect()` and migration
- **integrity_check = `ok`**
- Seed brand: `habitat` → display **Habitat / Habitat-Villas**
- Seed permissions (`can_create_plan`):
  - `amanda@wolfcommand.net` → `can_create_plan`
  - `haikalqilbari123@gmail.com` → `can_create_plan`
  - `mlsary111@gmail.com` → `can_create_plan`
  - `mrwolf@wolfcommand.net` → `can_create_plan`

## D. Memory governance rule
- Helper: `scripts/wolf_intelligence.py` → `write_memory_item`
- **RULE enforced:** `status=ACTIVE` only allowed when `approval_state=APPROVED`; otherwise demoted to PROPOSED
- Illegal ACTIVE rows now: **0**

## E. Habitat memory import (Phase 1B)
- Source: `/tmp/wolf-content-plans-for-chatgpt/Habitat-Villas/supporting/` (Brand + Strategy; FILM notes as PROPOSED OBSERVATION)
- `source_type=obsidian_export`, `source_id=filename`
- Clearly stated → FACT/RULE APPROVED+ACTIVE; otherwise PROPOSED OBSERVATION
- Counts:
  - memory_items total: **20**
  - ACTIVE+APPROVED: **14**
  - PROPOSED: **6**
  - FACT: **11** / RULE: **3** / OBSERVATION: **6**
  - evidence_items: **19**

## F. Permissions / identity (Phase 1C)
- `has_permission(subject, permission)` implemented
- `POST /api/planner/build-next` requires `X-Wolf-Subject` **or** JSON `subject`
- Missing/denied → **403** (no invented Cloudflare identity)
- **Gap documented:** CF JWT not wired; subject must be supplied until Access JWT is connected

## G. Dry skills (Phase 1D)
Package `scripts/skills/`:
- load_brand_memory, load_recent_plans, build_fortnight_strategy, generate_feed_cards, generate_story_spine, check_asset_status, validate_brand_rules
- `__init__.py` orchestrator
- Each returns `{result, evidence, confidence, assumptions, missing_information}`
- No provider names in skill output
- Cadence targets: **~3 feed / ~14 stories**
- Shot list note: *"Suggested coverage. Adapt based on conditions, talent and creative opportunities on location."*
- Honest **not connected** for performance / trends / inspiration

## H. APIs (Phase 1E–G) in `serve_beta.py`
| Method | Path | Notes |
|---|---|---|
| POST | `/api/planner/build-next` | permission gated; Working Draft |
| POST | `/api/planner/plans/{id}/edit` (+ `/revision`, `/api/plans/{id}/revision`) | HUMAN_EDIT |
| POST | `/api/planner/cards/{id}/edit` | HUMAN_EDIT; AI_PROPOSAL immutable |
| POST | `/api/planner/plans/{id}/approve` | HUMAN_APPROVED; **no publish** |
| GET | `/api/planner/plans/{id}` | Working Draft |
| GET | `/api/brands` | brand list |
- skill_runs logged per orchestrated skill
- No publish/render/Metricool write added

## I. UI (Phase 1H)
- `dashboards/content-2.0.html` — **Wolf Intelligence** view
- Habitat Build Next Plan button
- Subject email input (honest Phase 1 identity)
- Strategy + feed cards + story spine
- Edit card → HUMAN_EDIT; Approve Plan
- Checklist: wired steps = done; disconnected = placeholder
- No provider/agent codenames in Intelligence section

## J. Tests (Phase 1I)
- Suite: `scripts/tests/test_phase1_habitat.py`
- Results file: `/tmp/phase1-test-results.txt`
- **PASS=37 FAIL=0** (exit 0)
- Covers health, ports, schema, integrity, seeds, permission 403s, build-next cadence, FILM, revisions, approve-not-publish, skill_runs, UI labels

## K. Confirmation counts (post-test DB)
```
{
  "brands": 1,
  "permissions": 4,
  "memory_items": 20,
  "memory_active_approved": 14,
  "memory_proposed": 6,
  "memory_fact": 11,
  "memory_rule": 3,
  "memory_observation": 6,
  "evidence_items": 19,
  "content_plans": 3,
  "plan_revisions": 9,
  "plan_ai_proposal": 3,
  "plan_human_edit": 3,
  "plan_human_approved": 3,
  "content_cards": 51,
  "feed_cards": 9,
  "story_cards": 42,
  "card_revisions": 54,
  "card_ai_proposal": 51,
  "card_human_edit": 3,
  "skill_runs": 21
}
```
- Per successful build-next: feed=3, stories=14, skill_runs≥7, AI_PROPOSAL retained after HUMAN_EDIT

## L. LaunchAgent / process hygiene
- Restarted `net.wolfcommand.serve-beta` via `launchctl kickstart -k` (killed only :8788 beta)
- **Never killed PID 3758 / :8787**
- Health: `GET http://127.0.0.1:8788/api/health` → ok

## M. Gaps / Phase 2+ (honest)
- Cloudflare JWT identity not wired (subject header required)
- Performance / Metricool READ not connected
- Trend lanes / Inspiration library not connected
- No publish/schedule side effects (by design)
- Paid LLM live calls not used (dry deterministic skills)
- Obsidian vault not written

## N. STOP conditions
- integrity_check after migrate: **ok** — no restore required
- Backup ready at `catalog/backups/content_library.sqlite.bak-phase1-20260915-070530`

---

### Parent handoff summary
| Item | Value |
|---|---|
| Backup paths | see §B |
| integrity_check | ok |
| memory ACTIVE+APPROVED | 14 |
| feed cards (total DB) | 9 |
| story cards (total DB) | 42 |
| plan_revisions | 9 (AI=3, EDIT=3, APPROVED=3) |
| card_revisions | 54 |
| Tests | PASS=37 FAIL=0 |
| :8787 | untouched (PID 3758 alive) |
