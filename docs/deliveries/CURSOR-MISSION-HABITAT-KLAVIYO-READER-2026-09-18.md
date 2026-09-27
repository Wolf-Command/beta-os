# CURSOR MISSION — Habitat Klaviyo read-only ingestion v1

Date: 2026-09-18
Repo: /Users/wolfterminal/beta-os
Branch: build/wolf-command-rebuild
HEAD at start: 12ca489
Slice: habitat-klaviyo-reader-v1

This is a technical prove. It is not cutover.

## Do not

- Do not edit scripts/habitat-lead-sync.py or any atrium lead sync.
- Do not set, store, or activate operational cutover_at.
- Do not insert the 289 live profiles.
- Do not call the live Klaviyo network from tests or from any default command.
- Do not write the Sheet, ClickUp, Telegram, email, or Klaviyo.
- Do not create a work item. Do not call create_work_item or link_work_item.
- Do not grant any permission to a staff role. Do not touch ROLE-MATT.
- Do not import the board, the sheet, or historical profiles.
- Do not promote CAP-CRM-01. Do not edit the SYSTEM score files.
- Do not touch these dirty files: scripts/migrations/migrate_phase2_6_team_readiness.py, scripts/phase26_team.py, scripts/skills/__init__.py, scripts/wolf_intelligence.py.
- Do not git add . Do not stage unrelated untracked docs or state packs.
- Do not use --no-verify.

## Clock lock

For source system klaviyo, profile.created is lead received.
Store it on core_leads.source_observed_at.
Provenance must say the clock means RECEIVED_BY_KLAVIYO_SOURCE.
It does not prove the instant a human submitted an enquiry upstream.
wolf_ingested_at is wolf first seen, written once. Never copy it into source_observed_at.
Event recorded_at is the ingestion clock. It is not the receipt clock.

## Fix 1 — response_time

File: scripts/core/lead_spine.py function response_time.

Start time is source_observed_at only.
If first_human_touch_at is missing, return status UNAVAILABLE and seconds None.
If source_observed_at is missing, return UNAVAILABLE even when wolf_ingested_at is present.
Never subtract from wolf_ingested_at.

## Fix 2 — record_human_touch

Same file.

actor_type must be PERSON. SYSTEM raises. Default must not be SYSTEM.
verified_person_id is required.
touched_at is required. Do not call now_utc_iso to fill it.
If source_observed_at is missing, reject. Code invalid_chronology. Write nothing.
If touched_at is earlier than source_observed_at, reject. Code invalid_chronology. Write nothing.
Equal timestamps are allowed.
On success, set first_human_touch_at only when it is still null, and append event human_touch_recorded with the supplied time and the person id.

## New reader

New file: scripts/core/habitat_klaviyo_reader.py
Do not import habitat-lead-sync, clickup, sheets, or telegram.

Public function run_ingest(pages, *, entity_id, brand_id, boundary_at, conn).
boundary_at is required. No default of now.
entity_id for Habitat tests is ENT-GGV. brand_id is habitat.
source_system is the string klaviyo.
source_id is the profile id.
Email, when present, goes in provenance as an attribute only. It is not the key.

Each page is a dict shaped like the Klaviyo JSON:
data: list of {id, attributes: {created, email}}
links: {next: url or null}

Parse links.next as a real URL. Accept page[cursor] whether percent-encoded or not.
Do not require the substring page%5Bcursor%5D.
Empty or null next means the page is the last page.
A non-empty next that is not a usable URL is an error. The run stays INCOMPLETE. Do not mark complete.

No page cap. Walk every injected page until last page, error, or the stop rule below.

Newest-first assumption: stop after a fully persisted page whose every profile created time is strictly before boundary_at. Count those profiles as skipped. Do not insert them.
On a mixed page, insert only profiles with created >= boundary_at. Skip the earlier ones. Then continue.
A profile with no created time is an error for that record. Do not insert it. Do not treat the run as complete.

Call the existing ingest_observation.
source_stage is None. Never the string new. wolf_stage stays null.
observation_key is klaviyo:{profile id}:received
Provenance includes source klaviyo, clock profile.created, meaning RECEIVED_BY_KLAVIYO_SOURCE.

Do not call record_human_touch. Do not create a work item.
current_work_item_id stays null.

## Ledger

Same sqlite as the leads. New tables, new migration script scripts/migrations/migrate_habitat_klaviyo_reader.py.
Do not edit the phase26 migration.

Table core_lead_ingest_runs:
run_id, started_at, completed_at nullable, state (RUNNING, INCOMPLETE, COMPLETE),
cursor_next nullable, pages_examined, records_examined, inserted, already_present,
skipped, errors, oldest_source_at, newest_source_at, boundary_at, detail_json.

Cursor advances only after that page's inserts and skips are committed.
If a page raises before commit, do not move cursor_next past the last committed page, and state stays INCOMPLETE.

RUN FINISHED is not RUN COMPLETE. COMPLETE only when the stop rule is met with errors = 0.
A raised page, a malformed next link, or a missing created time leaves INCOMPLETE.

Resume: run_ingest accepts resume_run_id. Start from that run's cursor_next. Do not re-count already committed inserts as new inserts. Replay of a saved profile id stays one lead (ingest_observation created False).

## Probe

A function probe_readonly(fetch_page) may walk pages and return counts only.
It must not call run_ingest. It must not write core_leads.
No __main__ that talks to the network.
Tests never open the network. If urllib or the Klaviyo client is called, the test fails.

## Tests

New file scripts/tests/test_habitat_klaviyo_reader.py
Use an isolated temp sqlite. Follow the isolation style in scripts/tests/test_lead_spine.py.
Do not delete or rewrite the 8 fixture demo leads if a shared db is opened. Prefer the temp db so you never touch them.

Required cases:
- SYSTEM actor cannot record human touch
- missing touched_at cannot record human touch
- missing source_observed_at makes response_time UNAVAILABLE even if wolf_ingested_at is set
- missing first_human_touch_at makes response_time UNAVAILABLE
- touch before source_observed_at is rejected and not stored
- touch equal to source_observed_at is stored
- duplicate profile id on two pages is one lead
- failed second page does not advance the cursor, state INCOMPLETE
- resume after that failure does not create a second lead for page 1
- malformed next link leaves INCOMPLETE and does not claim COMPLETE
- a 3-page fixture with a real last page (next null) is COMPLETE and pages_examined is 3, and every profile id was examined
- profile created before boundary_at is not inserted
- no row gets source_stage new or wolf_stage set from this reader
- no work item row is created
- no permission grant row is created
- reader source does not call urlopen, clickup, sheets, or telegram

Run:
python3 -m unittest scripts.tests.test_habitat_klaviyo_reader scripts.tests.test_lead_spine
Both must be pass. Existing lead spine tests must still pass. Update them if they depended on the old SYSTEM default or the ingested-at fallback. That update is in scope.

## Commit

One commit. Message: feat(crm): add Habitat Klaviyo read-only reader
Stage only the files you created or edited for this slice.
Print the hash.
Do not push.

## Done line

Print exactly:
COMMIT: <hash>
TESTS: PASS=<n> FAIL=0
EXIT:0
