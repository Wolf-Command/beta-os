# CURSOR MISSION — Lead Spine v1

Owner accepted 18 Sep 2026. One lane. Fixtures only.

## Hard rules
- Workspace `/Users/wolfterminal/beta-os`, branch `build/wolf-command-rebuild`.
- Beta only. Path guard: refuse any DB path that does not contain `beta-os`, and refuse any path that contains `wolf-system`. Copy the guard used in `scripts/core/identity.py`.
- Do not edit these dirty files: `scripts/migrations/migrate_phase2_6_team_readiness.py`, `scripts/phase26_team.py`, `scripts/skills/__init__.py`, `scripts/wolf_intelligence.py`.
- Do not `git add .`. Stage only the files listed below.
- No network. No urllib calls. No Klaviyo, Sheets, ClickUp, Telegram, email, Meta, Google, ActiveCampaign.
- No Production files. No import of the 227 Habitat leads. No live role grants. Do not insert into `org_role_permissions` in the migration.
- Do not edit `scripts/core/scope.py` or `scripts/core/work_items.py`.
- Do not change Model C ledger, credits, or SYSTEM percentage files.
- Do not create an agent.
- Commit when tests are green. Message: `feat(crm): add Beta Lead Spine v1 fixtures`

## Files you may write
- `scripts/core/lead_spine.py`
- `scripts/migrations/migrate_lead_spine.py`
- `scripts/tests/test_lead_spine.py`
- `docs/SPEC-Lead-Spine-2026-09-18.md` (short canon restating this mission; no new rules)

## Objects
LEAD is not PERSON, not CUSTOMER, not SALE, not REVENUE.
Do not insert a lead into `org_persons`. Do not create an Authentication Identity for a lead.
Email or phone, if a fixture passes them, are source attributes only. They never merge leads.

## Tables
Create in the migration and in `ensure_schema(conn)` so tests can use a temp DB.

`core_leads` current projection:
- `lead_id` TEXT PRIMARY KEY
- `entity_id` TEXT NOT NULL
- `brand_id` TEXT NOT NULL
- `source_system` TEXT NOT NULL
- `source_id` TEXT NOT NULL
- `source_observed_at` TEXT NULL
- `wolf_ingested_at` TEXT NOT NULL
- `provenance_json` TEXT NOT NULL
- `source_stage` TEXT NULL
- `wolf_stage` TEXT NULL
- `owner_person_id` TEXT NULL
- `owner_assignment_id` TEXT NULL
- `first_human_touch_at` TEXT NULL
- `current_work_item_id` TEXT NULL
- `conversion_status` TEXT NULL
- `conversion_evidence_id` TEXT NULL
- UNIQUE (`entity_id`, `brand_id`, `source_system`, `source_id`)

Null means absent. Never write the string `UNKNOWN` into `owner_person_id`, `source_stage`, or `conversion_status`. Never write 0 as a default response time.

`core_lead_events` append-only:
- `event_id` TEXT PRIMARY KEY
- `lead_id` TEXT NOT NULL
- `event_type` TEXT NOT NULL
- `occurred_at` TEXT NULL
- `recorded_at` TEXT NOT NULL
- `actor_type` TEXT NOT NULL
- `actor_person_id` TEXT NULL
- `payload_json` TEXT NOT NULL
- `supersedes_event_id` TEXT NULL
- `observation_key` TEXT NULL
- UNIQUE (`lead_id`, `observation_key`) where observation_key is not null. Use a unique index that allows multiple nulls.

Triggers abort UPDATE and DELETE on `core_lead_events`.

`core_lead_stage_maps` reference rows, not live people:
- vocab id, source_stage verbatim, wolf_stage or null

## Wolf lifecycle (locked)
`OPEN`, `ACTIVE`, `PARKED`, `CLOSED` only.
`CLOSED` is outcome-neutral. It is not won, not lost, not bought, not a verified conversion, and not revenue.
No source word may change those meanings.

## Source stages (locked, keep all three visible)
1. Vocab `CONTENT-DEMAND-5`: codes `new`, `process`, `followup`, `parked`, `closed`.
2. Vocab `BAKE-8`: codes `new`, `contacted`, `qualified`, `viewing`, `offer`, `won`, `not_interested`, `parked`.
3. Vocab `IMPORT-NOTE-2026-08-21`: the words `new`, `in process`, `follow-up`, `parked`, `reserved/bought`. Do not rewrite these words into the content-demand codes.

Proposed map, now locked:
- `new` and `new` words → `OPEN`
- `process`, `followup`, `contacted`, `qualified`, `viewing`, `offer`, `in process`, `follow-up` → `ACTIVE`
- `parked` and word `parked` → `PARKED`
- `closed`, `won`, `not_interested`, word `reserved/bought` → `CLOSED`
Unmapped source text stays in `source_stage`. `wolf_stage` stays null. Do not coerce it to `new`.

## Events
`observed`, `assigned`, `stage_changed`, `human_touch_recorded`, `note_recorded`, `next_action_linked`, `conversion_claimed`, `conversion_verified`, `correction`, `match_candidate_recorded`, `match_candidate_revoked`.

Same source key returns the same lead.
Same `observation_key` is idempotent (no second event).
A different `observation_key` appends.
`stage_changed` payload stores source before, source after, wolf before, wolf after.
`correction` points at an old event. The old row stays byte-for-byte.
A payload containing an inference key (`inference`, `inferred`, `ai_guess`) is refused.

## Permissions
Insert codes only, status ACTIVE, no role rows:
- `lead.read` resource `lead` action `read`
- `lead.create` resource `lead` action `create`
- `lead.event.append` resource `lead` action `event.append`
- `lead.assign` resource `lead` action `assign`

Use stable ids `PERM-LEAD-READ`, `PERM-LEAD-CREATE`, `PERM-LEAD-EVENT`, `PERM-LEAD-ASSIGN`.
Call `rbac.evaluate`. Then require the winning assignment's scope targets include this `brand_id`. An entity-wide scope does not pass. Do not change `scope.py`.
Missing person, missing code, or wrong brand is denied.
No names, emails, or chat ids of Amanda, Matthew, Haikal, or anyone else in this module or migration.

## Work items
`current_work_item_id` is null or an existing `core_work_items.work_item_id`.
No `core_lead_tasks` table.
A lead may exist with no work item.
Linking appends `next_action_linked`. It does not insert a work item.

## Touch and speed
`human_touch_recorded` is the only writer of `first_human_touch_at`.
`response_time(lead)` returns `{"status":"UNAVAILABLE","seconds":None}` when touch is absent.
When both timestamps exist, seconds are touch minus `source_observed_at` if present, else minus `wolf_ingested_at`, and status is `MEASURED`.
A measured 0 is allowed only when the two evidenced timestamps are equal. Never invent 0.

## Conversion
`conversion_status` null, or `CLAIMED`, or `VERIFIED`.
`claim_conversion` sets `CLAIMED` and appends `conversion_claimed`. No amount field. Refuse an amount key.
`verify_conversion` requires a row in `core_evidence_records` with that `evidence_id`, `verification_status` = `VERIFIED`, `status` = `ACTIVE`, and `governed_object_id` = this `lead_id`. Otherwise refuse. Append `conversion_verified`.
Source stage `won`, `closed`, or `reserved/bought` must not set conversion.

## Identity
Automatic dedup is only `entity_id + brand_id + source_system + source_id`.
Same email, two brands: two leads.
Cross-source likeness appends `match_candidate_recorded`. It does not merge or overwrite. Revoke appends `match_candidate_revoked`.

## API
Expose functions, not HTTP:
`ingest_observation`, `append_event`, `set_stage`, `assign_owner`, `link_work_item`, `record_human_touch`, `claim_conversion`, `verify_conversion`, `record_match_candidate`, `revoke_match_candidate`, `correct_event`, `response_time`, `get_lead`, `read_lead` (permissioned), `honesty_flags`.
`honesty_flags` must say append_only true, live_import false, external_writes false, hardcoded_people false, closed_implies_conversion false.
PERSON calls require `verified_person_id` and the matching permission. Do not trust a client-supplied person id that differs.

## Migration
`migrate_lead_spine.py` targets `catalog/content_library.sqlite` by default and accepts an optional db path for tests.
Run it once on the Beta catalog so the tables and four permission codes exist.
Do not insert leads. Do not insert role grants.
Schema migrations table pattern: follow `scripts/migrations/migrate_work_items.py`.

## Tests
`scripts/tests/test_lead_spine.py`. Temp sqlite under `catalog/backups/tmp-lead-spine-<pid>/`. Never the live catalog.
Seed two brands: `habitat` and `fixture-selo`, both entity `ENT-GGV`.
Seed three persons in the temp DB only:
- brand scope habitat with all four lead permissions
- brand scope fixture-selo with all four
- entity scope ENT-GGV with `lead.read` granted, which must still be denied for a habitat lead

Required proofs (each is a PASS line):
1. Missing source system or source id refused.
2. Inference payload refused.
3. Ingest does not insert `org_persons`.
4. Habitat lead is denied for the fixture-selo person.
5. Same email attribute on two brands does not merge.
6. Match candidate revoke leaves both leads intact.
7. Blank owner stays null.
8. No touch → response UNAVAILABLE and seconds None.
9. Claim without verified evidence cannot verify.
10. Module source contains no `http`, `klaviyo`, `telegram`, `clickup`, `activecampaign`, `amanda`.
11. Calling the module against a path containing `wolf-system` is refused (use a string check if the path cannot be created; do not touch production).
12. Replay of the same source key does not create a second lead.
13. Same observation key twice is one event.
14. A second observation key appends one event and still one lead.
15. Source stage `reserved/bought` stored verbatim, not rewritten to `closed`.
16. Wolf stage set does not erase source stage.
17. All three vocabs are readable from `core_lead_stage_maps`.
18. Correction does not change the prior event payload.
19. Source of `lead_spine.py` and the migration contains no person name or chat id.
20. Lead exists with `current_work_item_id` null.
21. Link to an existing work item id. No `core_lead_tasks` table.
22. Fuzzy candidate does not change lead count.
23. Entity-wide person is denied `read_lead` on the habitat lead.
24. A lead can be `CLOSED` with `conversion_status` null.
25. The same lead can be `CLOSED` with `CLAIMED`.
26. A different lead can be `CLOSED` with `VERIFIED` only when Core evidence is `VERIFIED` and ACTIVE for that lead.
27. Source stage `won` can map wolf stage to `CLOSED` and still leave `conversion_status` null.
28. Unmapped source stage `banana` stays `banana` and wolf stage null.

Print `PASS=N FAIL=0` when green.

## Done
Run `python3 scripts/tests/test_lead_spine.py`.
Run `python3 scripts/migrations/migrate_lead_spine.py` on the Beta catalog only.
Commit only the four allowed files plus this mission if it is already untracked. Do not stage the dirty WIP or other untracked docs.
Print the commit hash, `PASS` and `FAIL` counts, then the line `CURSOR_DONE`.
Exit 0 only if FAIL=0.
