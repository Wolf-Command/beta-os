# WOLF Phase 2.5 UX Reset — Build Report

**When:** 2026-09-15 10:34:54 WITA  
**Target:** Beta OS Content Engine `:8788` only  
**Live URL:** https://beta.wolfcommand.net/content-2.0.html  
**Machine:** Wolfs-Mac-Studio.local (`36d8fa4b-2d58-4983-b227-e5bfa5495e78`)  
**Root:** `/Users/wolfterminal/beta-os/`

## Goal

Product UX for the content team (Haikal). Team sees **work**, not machinery.

## Backup (before changes)

- `catalog/backups/content-2.0.html.bak-phase2-5-ux-20260915-102918`
- `catalog/backups/serve_beta.py.bak-phase2-5-ux-20260915-102918`

## What changed

### UI — `dashboards/content-2.0.html` (full product SPA rewrite)

Persistent primary nav + brand selector:

1. **DASHBOARD** — current fortnight, brand, progress (posts X/3, stories Y/14), filming required, awaiting review, recent uploads. No analytics clutter.
2. **CONTENT PLAN** — primary surface. Header brand + date range + status + counts. **POSTS** group first (POST 1..N), then **STORIES** (STORY 1..14). Collapsed cards; click opens brief.
3. **CONTENT BRIEF** drawer — human fields only (GOAL, THEME, CONTENT TYPE, IDEA/CONCEPT, HOOK, SCENE/SLIDE, TEXT OVERLAYS, CTA, CAPTION, HASHTAGS, RECOMMENDED SHOT LIST + adapt note, PRODUCTION NOTES, EXISTING FOOTAGE, FOOTAGE NEEDED, INSPIRATION, STATUS, ASSIGNEE). No JSON. No AI_PROPOSAL / HUMAN_EDIT labels in UI.
4. **EDIT** — Edit → fields → Save Changes / Cancel. Backend still writes `HUMAN_EDIT` revisions invisibly.
5. **Status labels (user-facing):** NOT STARTED, NEEDS FILMING, READY, IN PRODUCTION, EDITING, READY FOR REVIEW, COMPLETE — stored as `workflow_status` in card body; revision role remains internal.
6. **LIBRARY** — search + filters; thumbnail grid from `/api/assets` with **paths stripped**.
7. **UPLOAD** — big dropzone + latest uploads (UPLOADING / CHECKING / READY / FAILED). Uses existing `/api/upload/remote` + staging.
8. **WOLF INTELLIGENCE** — creative assistant shell; prefills context from a card; honest about connected vs not-connected capabilities. **No provider names. No fake trends/inspiration.**
9. **BUILD NEXT PLAN** — management-only inside Content Plan when `can_create_plan`. **Existing Working Drafts** list is primary (open without regenerating).
10. Technical checklist collapsed to one line: *"Plan prepared using available brand, historical and performance information."*
11. Clear empty states throughout.

### Backend — `scripts/serve_beta.py` (additive)

New GET APIs:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/planner/plans?brand=` | List content plans (operational preferred, test lane marked) |
| `GET /api/planner/plans/{id}?ux=1` | Existing draft + `ux` shape (posts then stories, briefs, progress) |
| `GET /api/planner/cards/{id}` | Human brief fields |
| `GET /api/planner/dashboard?brand=` | Dashboard summary |
| `GET /api/me/capabilities` | `can_create_plan` for management UI |

Also:

- `/api/assets` response **strips** `original_path` / `v2_path` (UI must not see filesystem paths).
- UX helpers map asset/card state → team-facing workflow status without exposing AI/HUMAN roles.

### Skills — `scripts/skills/__init__.py`

`human_edit_card` accepts expanded brief keys (`goal`, `theme`, `idea`, `workflow_status`, overlays, CTA, hashtags, production notes, footage fields, etc.) while still writing `HUMAN_EDIT` revisions.

## Acceptance (Habitat plan #9)

Proven against `http://127.0.0.1:8788`:

| Check | Result |
|-------|--------|
| Nav labels present in HTML | PASS |
| Posts 3 + Stories 14 on plan 9 UX | PASS (`POST 1..3`, `STORY 1..14`) |
| Open post brief fields | PASS (`/api/planner/cards/137`) |
| Edit flow → invisible HUMAN_EDIT revision | PASS (card_revisions 157–158) |
| Library assets, no paths | PASS |
| Upload / staging list UI wired | PASS (existing APIs) |
| Wolf Intelligence honest shell | PASS (no provider strings in HTML) |
| No openai/anthropic/claude/gpt/metricool/AI_PROPOSAL/HUMAN_EDIT in HTML | PASS |
| `8787` untouched | PASS (PID 3758 unchanged) |
| No Metricool write / no publishing | PASS (not invoked) |
| DB preserved | PASS (plans 9, cards 153, memory 20, performance 1103, card_revisions 158) |

### Sample curl

```bash
curl -s 'http://127.0.0.1:8788/api/planner/plans?brand=habitat' | jq '.count,.plans[0].id,.plans[0].posts,.plans[0].stories'
curl -s 'http://127.0.0.1:8788/api/planner/plans/9?ux=1' | jq '.ux.counts,.ux.posts[0].label,.ux.stories|length'
curl -s 'http://127.0.0.1:8788/api/planner/cards/137' | jq '.card.brief|keys'
curl -s 'http://127.0.0.1:8788/api/planner/dashboard?brand=habitat' | jq '.current_plan.plan.progress'
curl -s 'http://127.0.0.1:8788/api/assets?brand=habitat' | jq 'has("assets"), (.assets[0]|keys)'
```

## Safety / forbidden

- **Did not** destroy Phase 1/2 tables or APIs (memory, revisions, Metricool read sync, snapshots, permissions remain).
- **Did not** touch `:8787`.
- **Did not** perform Metricool write, publish, or Grok-agent wiring.
- UI does **not** expose providers, models, agents, Metricool, or skill names.

## Restart

- Stopped previous `serve_beta` on `:8788` only; started PID listening on `:8788`.
- `:8787` PID **3758** unchanged.

## Notes for Haikal / demo

- Habitat current operational plan is **#9** (2026-09-14 → 2026-09-27) with 3 posts + 14 stories.
- Test-lane plans (#1–3) still listed under Working Drafts with a subtle **DEV** badge.
- Default subject in UI localStorage for edit capability: `haikalqilbari123@gmail.com` (has `can_create_plan`).
- Wolf Intelligence panel is intentionally dry — lists what existing APIs support; does not invent trends.

## Files touched

- `dashboards/content-2.0.html`
- `scripts/serve_beta.py`
- `scripts/skills/__init__.py`
- Report: `/tmp/WOLF-PHASE2-5-UX-RESET-REPORT.md` + `dashboards/deliveries/WOLF-PHASE2-5-UX-RESET-REPORT.md`
