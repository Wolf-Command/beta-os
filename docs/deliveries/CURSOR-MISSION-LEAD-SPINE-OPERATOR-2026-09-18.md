# CURSOR MISSION — Lead Spine operator path

Owner authorised 18 Sep 2026 after discovery. One lane.

## Discovery already done
- Beta serves `127.0.0.1:8788` via `scripts/serve_beta.py`. Not port 8787.
- Live auth is `cloudflare_access`. `development_assertion_allowed` is false. Do not set `BETA_AUTH_MODE`. Do not restart into development assertion.
- `dashboards/habitat-operator.html` is the UI pattern: one file, inline CSS, max-width 640px, big buttons, status pills. Copy that look. Do not edit `habitat-operator.html`.
- `scripts/core/lead_spine.py` already has the spine. Reuse it. Do not replace it.

## Hard bounds
- Beta only. No Production. No `wolf-system` path.
- No live Habitat/Klaviyo/Sheet import. No external writes. No Telegram, email, ClickUp, Meta, Google.
- Do not grant `lead.*` to any existing staff role, including `ROLE-MATT`.
- Do not edit the four dirty files: `scripts/migrations/migrate_phase2_6_team_readiness.py`, `scripts/phase26_team.py`, `scripts/skills/__init__.py`, `scripts/wolf_intelligence.py`.
- Do not edit Model C or Model E files. Do not change the SYSTEM score.
- Do not `git add .`.

## Build
1. `dashboards/lead-spine.html` — mobile page. Human words first. Demo banner at the top: "Demo data. Not live leads."
2. Routes in `scripts/serve_beta.py` only, beside the habitat-operator aliases:
   - `GET /lead-spine` and `/lead-spine/` serve the page.
   - `GET /api/leads?brand=habitat` list for the signed-in person.
   - `GET /api/leads/<id>` one lead plus events.
   - `POST /api/leads/<id>/touch`
   - `POST /api/leads/<id>/note`
   - `POST /api/leads/<id>/stage` body `wolf_stage` only. Must not change `source_stage`.
   - `POST /api/leads/<id>/assign` and `POST /api/leads/<id>/unassign`
   - `POST /api/leads/<id>/work-item` links an existing Core work item id. Does not create one.
   - `POST /api/leads/<id>/claim` sets CLAIMED. No amount. No verify button that skips evidence.
3. Identity comes from the existing `resolve_request_identity`. No new login. No person id from the browser body.
4. Permission denied is a clear sentence, HTTP 403. Wrong brand is 403. Empty list is a clear empty state, not a fake lead.
5. List shows, in words: demo label, Wolf lifecycle, source stage, owner or Unassigned, conversion or none, response time or "unavailable". Database ids are secondary, not the title.
6. Source stage and Wolf lifecycle are visually separate. Closed copy must say closed is not a sale and not verified revenue.
7. Add `list_leads` if missing. Add unassign only if `assign_owner` cannot clear. Both append events. No history rewrite.

## Fixtures
Seed exactly these 8 demo leads on brand `habitat`, entity `ENT-GGV`, `source_system` = `fixture`. Idempotent. Provenance includes `"demo": true`. Labels start with `DEMO`.
1. Open, unassigned, source stage `new`, no touch.
2. Active, assigned to the demo person, source stage `process`.
3. Parked, source stage `parked`.
4. Closed, conversion null, source stage `closed`.
5. Closed, conversion CLAIMED, source stage `won`.
6. Closed, conversion VERIFIED, source stage `reserved/bought`, with one ACTIVE VERIFIED evidence row whose governed object is that lead.
7. Open or Active with no touch, so the page shows unavailable, not 0.
8. Source stage `banana`, Wolf stage null.

Create one fixture person `PERS-LEAD-DEMO`, display name `Demo operator`, no authentication email, no Cloudflare binding. Give that person only the four `lead.*` codes, scoped to brand `habitat`, in a new fixture role. Do not attach that role to Matthew or any staff person.
A second brand is not seeded in the live catalog. Cross-brand denial stays in the temp test database.

## Tests
`scripts/tests/test_lead_spine_operator.py` on a temp sqlite under `catalog/backups/`. Cover:
- list hides the other brand
- denied person gets 403 from the API function used by the route
- touch, note, wolf stage change, source stage unchanged
- assign and unassign
- link existing work item, no new task table
- claim does not verify
- verified fixture shows verified
- missing touch is unavailable
- unmapped source stays `banana`
- page file contains the demo banner and the closed-is-not-a-sale sentence
- seed does not insert a real staff grant

## Deploy proof
After the code is in place, restart the existing Beta process on `127.0.0.1:8788` only. Same command: `python3 scripts/serve_beta.py` from `/Users/wolfterminal/beta-os`. Do not pass `BETA_AUTH_MODE`. Do not touch port 8787.
Then curl:
- `GET /lead-spine` is 200 and the body contains `Demo data` and `not a sale`
- `GET /api/leads?brand=habitat` with no cookie is 403
Write those status codes into the cursor log.

## Commit
Message: `feat(crm): add Beta Lead Spine operator path`
Stage only the new page, the serve route edit, the spine list/unassign edit if any, the seed/migration, the test, and this mission if needed.
Print `PASS=` `FAIL=` the commit, the two curl codes, then `CURSOR_DONE`.
Exit 0 only if tests are green and `/lead-spine` is 200.
