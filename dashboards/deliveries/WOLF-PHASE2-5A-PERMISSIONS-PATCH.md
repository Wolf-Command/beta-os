# WOLF Phase 2.5A Permissions Patch — Build Report

**When:** 2026-09-15 10:43:58 WITA  
**Target:** Beta OS Content Engine `:8788` only  
**Live URL:** https://beta.wolfcommand.net/content-2.0.html  
**Machine:** Wolfs-Mac-Studio.local (`36d8fa4b-2d58-4983-b227-e5bfa5495e78`)  
**Root:** `/Users/wolfterminal/beta-os/`

## Goal

Data-driven permissions (emails as subjects), server gates on mutating endpoints, operational-lane UX filter, Approve Plan UI label **APPROVED**. No Phase 3. No Metricool write. No Cloudflare. No UX redesign. No delete test plans. No `:8787`.

## Backup (before edits)

- `catalog/backups/serve_beta.py.bak-phase2-5a-permissions-20260915-104050`
- `catalog/backups/wolf_intelligence.py.bak-phase2-5a-permissions-20260915-104050`
- `catalog/backups/content-2.0.html.bak-phase2-5a-permissions-20260915-104050`
- `catalog/backups/permissions.dump-phase2-5a-20260915-104050.sql`

## Permission matrix (seeded)

| Subject | Grants |
|---|---|
| `mrwolf@wolfcommand.net` (Matt) | can_create_plan, can_edit_plan, can_approve_plan, can_view_plan, can_update_production, can_upload, can_use_wolf_intelligence |
| `amanda@wolfcommand.net` | same as Matt |
| `haikalqilbari123@gmail.com` | all of the above **EXCEPT** can_create_plan |
| `mlsary111@gmail.com` | all of the above **EXCEPT** can_create_plan |

- Removed `can_create_plan` from Haikal + Misa (was phase1-seed).
- Migration: `scripts/migrations/migrate_phase2_5a_permissions.py` (idempotent).
- `permissions` rows now: **26**

```
amanda@wolfcommand.net → can_approve_plan, can_create_plan, can_edit_plan, can_update_production, can_upload, can_use_wolf_intelligence, can_view_plan
haikalqilbari123@gmail.com → can_approve_plan, can_edit_plan, can_update_production, can_upload, can_use_wolf_intelligence, can_view_plan
mlsary111@gmail.com → can_approve_plan, can_edit_plan, can_update_production, can_upload, can_use_wolf_intelligence, can_view_plan
mrwolf@wolfcommand.net → can_approve_plan, can_create_plan, can_edit_plan, can_update_production, can_upload, can_use_wolf_intelligence, can_view_plan
```

## Server gates (`serve_beta.py`)

General helper: `_require_permission(permission, body)` via `has_permission` + `resolve_authenticated_subject`.

**X-Wolf-Subject / JSON subject = DEVELOPMENT ONLY** (commented clearly). Cloudflare Access JWT **not** wired this phase.

| Endpoint | Permission | Unauthorized |
|---|---|---|
| `POST /api/planner/build-next` | `can_create_plan` | 403 |
| `POST /api/planner/plans/{id}/edit` | `can_edit_plan` | 403 |
| `POST /api/planner/cards/{id}/edit` | `can_edit_plan` (+ `can_update_production` if `workflow_status` in patch) | 403 |
| `POST /api/planner/plans/{id}/approve` | `can_approve_plan` | 403 |
| `POST /api/planner/cards/{id}/production-status` | `can_update_production` | 403 |
| `POST /api/upload/remote` | `can_upload` | 403 |
| `POST /api/llm/generate` | `can_use_wolf_intelligence` (prepare) | 403 |
| Admin Metricool sync (unchanged) | `can_create_plan` | 403 |

Approve API response: `status_label` / `ui_status` = **APPROVED**; DB status remains `Human_Approved`; revision role remains `HUMAN_APPROVED`. `published: false`.

`GET /api/me/capabilities` returns full permission bitset for UI.

## UX filter (small — no redesign)

- `GET /api/planner/plans` defaults to `data_lane=operational` only (hides test fixtures #1–3 from normal UI). Pass `data_lane=all` for dev.
- Dashboard / Wolf Intelligence context: operational lane **only**. Habitat operational plan primary (**#9**).
- Test rows **kept** in DB (`data_lane=test`).
- **Build Next Plan** panel only if `can_create_plan`; else empty-state copy for Haikal/Misa.
- **Approve Plan** button if `can_approve_plan`; confirm: *"Approve this fortnight plan for the team?"*; UI shows **APPROVED** (not HUMAN_APPROVED).

## Tests (Matthew checklist)

Script: `scripts/tests/test_phase2_5a_permissions.py`  
Log: `/tmp/WOLF-PHASE2-5A-TEST-OUT.txt`

```
PASS  01 health
PASS  02 :8788 listening
PASS  03 :8787 PID 3758 untouched — /opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Py
PASS  04 Haikal+Misa NO can_create_plan
PASS  05 Matt+Amanda HAVE can_create_plan
PASS  06 all four can_approve+can_edit
PASS  07 all four upload/prod/view/wi
PASS  08 Haikal capabilities flags — {"can_create_plan": false, "can_approve_plan": true, "can_edit_plan": true}
PASS  09 Matt can_create_plan true
PASS  10 plans default operational hides 1-3 — ids=[9, 8, 7, 6, 5, 4]
PASS  11 test plans 1-3 still in DB — 3
PASS  12 dashboard Habitat operational plan — id=9 lane=operational
PASS  13 Haikal build-next 403 — st=403 err=forbidden
PASS  14 build-next missing subject 403
PASS  15 Haikal card edit 200 — st=200
PASS  16 stranger card edit 403
PASS  17 stranger production-status 403
PASS  17b Haikal production-status 200
PASS  18 Haikal approve → APPROVED label — st=200 label=APPROVED db=Human_Approved
PASS  19 upload missing subject 403 — st=403 body={'ok': False, 'error': 'missing_subject', 'message': 'Provide X-Wolf-Subject header or JSON subject email (DEVELOPMENT ONLY). Cloudflare Access JWT not wired yet.', 'required_permission': 'can_upload'}
PASS  19b upload stranger 403
PASS  20 llm generate stranger 403 wi
PASS  20b Haikal llm generate not 403 — st=200
PASS  UI Approve confirmation copy
PASS  UI no Metricool write / no CF invent in serve gate comments
PASS  DB plan count preserved (>=9) — 9
TOTAL PASS=26 FAIL=0
```

**TOTAL PASS=26 FAIL=0** (20 numbered gates + UI/DB confirmations).

## Restart

- Stopped previous `serve_beta` on `:8788` only; started PID **"18209"**.
- `:8787` PID **3758** unchanged (was 3758 before; still 3758).

## Counts

| Item | Value |
|---|---|
| permissions rows | 26 |
| content_plans | 9 |
| test-lane plans | 3 (ids 1–3 kept) |
| Habitat operational primary | plan #9 |

## Safety / forbidden — confirmations

- **Did not** touch `:8787` (PID 3758 unchanged).
- **Did not** Metricool write / schedule / publish.
- **Did not** Cloudflare / Access JWT wiring.
- **Did not** delete test plans #1–3 (still in DB, `data_lane=test`).
- **Did not** start Phase 3 / UX redesign / Grok-agent wiring.
- **Did** backup `serve_beta.py` + permissions-related files before edit.
- Identity path remains **DEVELOPMENT ONLY** (`X-Wolf-Subject`).

## Files touched

- `scripts/serve_beta.py`
- `scripts/wolf_intelligence.py` (`list_permissions` / `KNOWN_PERMISSIONS`)
- `scripts/migrations/migrate_phase2_5a_permissions.py`
- `dashboards/content-2.0.html` (Approve button + capability flags + status label)
- `scripts/tests/test_phase2_5a_permissions.py`
- Report: `/tmp/WOLF-PHASE2-5A-PERMISSIONS-PATCH.md` + `dashboards/deliveries/WOLF-PHASE2-5A-PERMISSIONS-PATCH.md`

## STOP

Phase 2.5A complete. No next phase.
