# GROK REVIEW — Habitat Klaviyo read-only reader c58cc62

**Commit:** `c58cc62` feat(crm): add Habitat Klaviyo read-only reader
**Date:** 2026-09-18 (factory watch ADVANCE → GROK_REVIEW)
**Bound:** habitat-klaviyo-reader-v1
**Verdict:** **PASS**

## Diff vs mission

| Requirement | Present in c58cc62 | Result |
| --- | --- | --- |
| `response_time` uses `source_observed_at` only (never `wolf_ingested_at`) | start = source_observed_at; missing → UNAVAILABLE | PASS |
| Missing `first_human_touch_at` → UNAVAILABLE | early return | PASS |
| `record_human_touch` default PERSON; SYSTEM raises | default PERSON + invalid_actor | PASS |
| `verified_person_id` + `touched_at` required; no now fill | both enforced | PASS |
| Touch before `source_observed_at` rejected; equal allowed | invalid_chronology / equal stored | PASS |
| New `scripts/core/habitat_klaviyo_reader.py` | 448 lines; no sync/clickup/sheets/telegram imports | PASS |
| `run_ingest(pages, *, entity_id, brand_id, boundary_at, conn)` | required kwargs; no now default | PASS |
| source_system klaviyo; source_id = profile id; email in provenance only | as specified | PASS |
| Clock RECEIVED_BY_KLAVIYO_SOURCE on profile.created | CLOCK/CLOCK_MEANING constants | PASS |
| Usable next URL; empty/null = last; bad next → INCOMPLETE | `_classify_next` + tests | PASS |
| Boundary stop / mixed page / missing created | stop + skip + INCOMPLETE | PASS |
| `ingest_observation`; source_stage None; no human touch / work item | as specified | PASS |
| Ledger `core_lead_ingest_runs` + migration (no phase26 edit) | migrate_habitat_klaviyo_reader.py | PASS |
| Cursor advances only after page commit; resume | cursor_next + resume_run_id | PASS |
| COMPLETE only stop-rule + errors=0 | FINISHED ≠ COMPLETE | PASS |
| `probe_readonly` counts only; no network `__main__` | present; no `__main__` | PASS |
| Dirty WIP four files untouched | not in commit | PASS |
| No live Klaviyo / cutover / 289 profiles / CAP score | not in commit | PASS |
| One commit message exact | feat(crm): add Habitat Klaviyo read-only reader | PASS |

## Soft note (not FAIL)

Unrelated dirty tree files remain unstaged (phase26 / skills / wolf_intelligence + docs packs). Commit staged only the five slice files. Migration reports existing staff_grants count (before/after equality guard) — does not grant.

## Red team

| Attack | Result |
| --- | --- |
| SYSTEM records human touch | PASS — invalid_actor |
| Touch without touched_at / before receipt | PASS — rejected, no write |
| response_time falls back to wolf_ingested_at | PASS — UNAVAILABLE without source_observed_at |
| Malformed next claims COMPLETE | PASS — INCOMPLETE |
| Failed page 2 advances cursor / doubles page-1 lead on resume | PASS — cursor held; one lead |
| Profile before boundary inserted | PASS — skipped |
| source_stage=new / work item / role grant | PASS — none |
| urlopen / clickup / sheets / telegram from reader | PASS — tokens absent; test asserts |
| Demo fixture leads mutated | PASS — temp db; 8 fixtures unchanged |
| Dirty WIP / Production / habitat-lead-sync | PASS — not in commit |

## Verification

- `python3 -m unittest scripts.tests.test_habitat_klaviyo_reader scripts.tests.test_lead_spine` → **20 tests OK** (re-run 2026-09-18 13:30 WITA); habitat suite alone **19 OK**; lead_spine harness **PASS=33 FAIL=0**
- Cursor log: EXIT:0 after commit `c58cc62`
- Files: habitat_klaviyo_reader.py, lead_spine.py (±55), migrate_habitat_klaviyo_reader.py, test_habitat_klaviyo_reader.py, test_lead_spine.py (+6)

## Out of scope leftovers

Live Klaviyo network ingest; operational cutover_at; importing 289 live profiles; Sheet/ClickUp/Telegram writers; staff grants; CAP-CRM-01 / SYSTEM score — still blocked by bound. Technical prove only.
