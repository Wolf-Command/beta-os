# RESULT — Content Engine upload state + Library search

Run: `BF-content-engine-upload-state-library-search-20261001`
Date: 2026-10-01
staff_ready: false
Haikal retest: HOLD until Peaches verifies this pack
Prod :8787: not touched (pid 15975 still listening)
Prior ffmpeg commit kept: `e0896ae`
This pack commit: `9df39108a63ca1e365ee5e2a859341a4fab62fd0` on `build/wolf-command-rebuild`. No remote is configured, so it was not pushed.

## Root causes fixed

1. **Store success was reported as an upload failure.** After the file was on the NAS and in `assets`, a poster miss set `library_available` false. The Content page treated that as a failed file and Retry sent the bytes again. The lifecycle had no separate DERIVATIVE FAILED state.
2. **Library search was not one server-side query.** `GET /api/assets` appended every matching catalog row to a NAS page, and an older loader filtered that list in the browser. Search did not cover the real indexed columns. A shoot-date filter compared the raw string, so `2026-08-01` missed rows stored as `20260801`, and cards filled a blank shoot date from the upload date.
3. **The BBQ count gap is not a missing poster.** Batch `bmuowp00n` has 12 Tropik `bbq-night-grill` rows. Each file is on the NAS at the recorded size, each row is indexed, and each has a poster. The access log records `POST /api/upload/smart` status only, so the other two filenames in the owner’s “14” are UNKNOWN.

## What changed

- `scripts/core/content_engine_repair.py` — canonical stages RECEIVED / UPLOADING → FILE STORED → INDEXED → DERIVATIVES PROCESSING → READY, with STORAGE FAILED, INDEX FAILED, and DERIVATIVE FAILED. Poster miss after store keeps `ok` and `file_stored`, sets `upload_failed` false, and returns “Video uploaded successfully. Preview processing failed — Retry Preview.” `retry_asset_preview` rebuilds the poster for that asset id. `library_search` is one AND query, case-insensitive, page size at most 48. `reconcile_bbq_batch` inventories the batch and only generates a poster when the NAS file and the row already exist.
- `scripts/serve_beta.py` — `GET /api/assets` uses that search. `POST /api/assets/{id}/retry-preview` does not accept a new file.
- `dashboards/content-2.0.html` — lifecycle list, Retry Preview on the stored asset, server-paged Library. Cards show thumb, title, brand, footage date, type, and status. A blank shoot date stays UNKNOWN. Asset view holds the field dump. Empty search is not a client-side filter.
- `scripts/tests/test_content_engine_upload_state_library_20261001.py`

## BBQ reconcile

Source: live `catalog/content_library.sqlite` and the NAS paths on those 12 rows, read 2026-10-01. Report: `state/build-factory/BBQ-RECONCILE-bbq-night-grill-20261001.json`.

| Check | Count |
|---|---|
| Owner reported | 14 |
| Catalog rows (batch `bmuowp00n`, seq 001–012) | 12 |
| On NAS, size matches `file_size` | 12 |
| Indexed | 12 |
| Poster present | 12 |
| Duplicate content hashes | 0 |
| Deterministic repairs applied | 0 (posters already present; sizes unchanged) |
| Pre-storage failures with a known filename | 0 |
| Unknown gap | 2 filenames, not invented, not marked successful |

Human review: the two missing names. No delete. No force-success. Batch provenance left as 12 rows.

## Prove

| Gate | Result | What was checked |
|---|---|---|
| U1 | PASS | Poster forced to fail after NAS store. HTTP 200, `upload_failed` false, `DERIVATIVE_FAILED`, staff sentence, NAS size matched. Not counted as a full upload fail. |
| U2 | PASS | Retry Preview on that asset id. Same row, same NAS size, poster written. Second retry did not add a row. |
| U3 | PASS | NAS miss stays STORAGE FAILED with “Storage is unavailable. Nothing new was saved for this file.” |
| U4 | PASS | One file stayed library-ready, one was DERIVATIVE FAILED and stored, a same-byte resend returned 409. |
| U5 | PASS | `test_content_engine_upload_14fail_20261001.py --live` 33 pass / 0 fail. `test_content_engine_haikal_fail_repair.py` 72 pass / 0 fail. |
| B1 | PASS | 12 rows, 12 on NAS, 12 indexed, 12 posters. |
| B2 | PASS | No poster rewrite. UNKNOWN gap written for review. |
| B3 | PASS | `force_success` false, `deleted` false, batch id `bmuowp00n`, no duplicate hashes. |
| L1 | PASS | Empty `q`, brand tropik: matched 1700, page showed 48. |
| L2 | PASS | `BBQ-NIGHT-GRILL` matched 12. `img_3801` matched the camera name. Content class `FOOD` matched a stored provenance value in the temp library. |
| L3 | PASS | video narrowed 1700 → 848. Image + bbq query matched 0. RAW + bbq matched 12. FINAL + bbq matched 0. |
| L4 | PASS | Temp row with only an upload date did not match shoot date `2026-10-01`. Live bbq rows matched `2026-08-01` (12) and did not match `2026-10-01` (0). |
| L5 | PASS | Atrium matched 32610. Page size 48. Page 2 was a different slice. Limit 500 still returned 48. |
| L6 | PASS | The probe uploads were found by brand tropik + `eng-upload-state` + shoot date `2026-10-01` on the test lane. Probe rows were then removed. |
| L7 | PASS | Select all and `POST /api/assets/zip` remain in the page and the server. |

This pack: 41 pass / 0 fail. Evidence: `state/commissioning/evidence/CE-UPLOAD-STATE-LIBRARY-SEARCH-GATE-2026-10-01.json`.

## Beta deploy

`launchctl kickstart -k gui/501/net.wolfcommand.serve-beta`

Listening pid is 60095 on 127.0.0.1:8788. Prod pid 15975 is still on 127.0.0.1:8787.

`GET /api/content/repair-status` after restart: `upload_state_run_id` is this run, `ffmpeg_resolved` true, `staff_ready` false. Unsigned `POST /api/upload/smart` and `GET /api/assets` are 403 `missing_auth`.

## Residuals

- Haikal has not retested. staff_ready stays false. No Exit Report. Do not ping Haikal.
- The two MOV names in the owner’s “14” that never became catalog rows are UNKNOWN.
- A logged-in browser upload was not clicked. The byte pipeline was proved in-process under the launchd PATH, and the listening process reports this run id.
- Sibling uncommitted work on the Beta tree was left unstaged.
