# P1 — Content Engine NAS media estate — 27 Sep 2026

Extends the 2026-09-22 NAS commissioning rule and the 26 Sep in-place indexer. Beta catalog only. Production :8787 (pid 15975) was not restarted. No NAS file was moved, renamed, or deleted. The one new file written on the NAS is the Smart Upload test image under the existing `_Imports/Wolf-Library` prefix. `staff_ready` stays false.

ENGINEERING PASS. Not staff ready. Not human commissioned.

## BEFORE

Measured on the Beta catalog at the start of this run (owner counts `2026-09-26T10:30:44+08:00`, phase `caught_up`):

| | |
| --- | ---: |
| catalog rows | 63370 |
| HASHED | 29146 |
| FAILED | 34224 |
| SEARCHABLE | 0 |

FAILED reasons: `missing_file:not_found` 34208, `thumb_failed` 15, `thumb_timeout` 1. Every `missing_file:not_found` row had `source_root` `01-Media-Library` and `indexed_at` `2026-09-26T00:34`. A random sample of those paths was a regular file on disk.

`indexed_at` is the original ingest stamp. `mark_failed` does not change it, so the stamp does not mean the row was never visited after `da938ff`.

What `da938ff` actually did: the 08:33 requeue log shows `resolved=40000` with `missing=0`, and the following enrich started with 41890 `INDEXED` rows. A second start at 08:34:48 then logged `requeue resolved=0` because those rows were already `INDEXED`, not because they had been skipped. From `2026-09-26T09:31:29` the thumb pass called `resolve_media_path`, got `missing_file:not_found` (a `FileNotFoundError` from the share, which is not in the transient errno set), and `mark_failed` left them `FAILED`. Requeue ran only at process start. The run reached `caught_up` at 10:30 and did not look at those rows again.

## BUILT-REPAIRED

- An unmounted `/Volumes/<share>` is `missing_file:volume_unavailable` and stays retryable. It is not a deleted file.
- A `not_found` on a share that is still a directory is retried before it is stored as permanent. A path that is still absent stays `FAILED` / `missing_file:not_found`.
- Before `caught_up`, stale `missing_file*` rows and `hash_error:FileNotFoundError` / `hash_error:TimeoutError` rows are rechecked. If the file resolves, the row returns to `INDEXED`. `thumb_failed` and `thumb_timeout` are not put back on the queue.
- Thumbnails for photos and videos are written under `state/content-thumbs`. Raw, PDF, and other non-raster files become searchable with `preview_note=no_raster_preview` and do not block the run. Corrupt or timed-out renders are `FAILED` and listed in `state/nas-estate/exceptions.json`.
- Folder evidence mapped 538 previously `UNKNOWN` or blank rows: Uma Blu / Atrium Lombok folder phrases, `BZG/.../01 Blu Zone` → rainforest, intake prefixes (`umablu_drop_`, `habitat_drop_`, `tropik_drop_`, `atrium_drop_`, `selongselo_drop_`), and `goss group` in a filename. A brand word inside an unrelated filename stays `UNKNOWN`.
- Creative Director library cards for NAS photos and videos can be selected. Individual download uses `Content-Disposition: attachment`. Multi-select ZIP accepts `nas:<id>` and reads the file. Nothing under a NAS tree is written by the ZIP.

Startup requeue at `2026-09-26T22:43:47+08:00`: `resolved=34208 missing=0 transient=0`. A later flake during the run marked 788 rows missing or hash-not-found; the next start requeued all 788 (`missing=0`). The final recheck at `2026-09-27T02:35:02` put 9 remaining hash-not-found rows back, processed them, and the following recheck was `resolved=0 missing=0`.

## VERIFIED

Unit tests, after the recheck and brand-mapping code:

```
python3 scripts/tests/test_nas_estate_index.py | tail -3
PASS  search still hits hashed selo — 1
PASS  search still hits hashed habitat — 1
EXIT: SUCCESS PASS=51 FAIL=0
```

Indexer log:

```
2026-09-27T02:35:02+08:00 recheck resolved=9 missing=0 transient=0
2026-09-27T02:35:06+08:00 enrich thumbs=9 hashes=9 promoted=9 remaining={'INDEXED': 0, 'THUMB_PREVIEW_READY': 0, 'THUMBNAIL_READY': 0, 'SEARCHABLE': 0}
2026-09-27T02:35:06+08:00 recheck resolved=0 missing=0 transient=0
2026-09-27T02:37:13+08:00 caught up catalog_rows=63370 failed=124 exceptions=124 unknown_brand=4787 inaccessible=0
```

Catalog after caught_up: `HASHED` 63246, `FAILED` 124. Fail reasons: `thumb_failed` 107, `thumb_timeout` 15, `hash_error:OSError` 2. `missing_file:not_found` remaining: 0. `no_raster_preview`: 2766. `thumb_ready=1`: 60474.

`state/nas-estate/FINAL-TRUTH-20260927.json` (`as_of` `2026-09-27T02:37:13+08:00`):

| field | measured |
| --- | ---: |
| discovered | 63370 |
| processed | 63370 |
| searchable | 63246 |
| preview_ready | 63246 |
| thumbnail_ready | 60474 |
| genuine_failures | 124 |
| unknown_brand | 4787 |
| inaccessible | 0 |

`preview_ready` counts rows that finished the preview step (`HASHED`). `thumbnail_ready` counts a jpeg in the thumb cache. The gap is mostly `no_raster_preview` (camera raw, PDF, and similar). Those rows are still searchable by name. They do not have a picture thumbnail.

Brand × state (rows with no files are absent from the SQL group; The One is present in the truth file as an empty object):

| brand | HASHED | FAILED |
| --- | ---: | ---: |
| atrium | 32608 | 84 |
| umablu | 8687 | 21 |
| selo | 6519 | 5 |
| SHARED_STOCK | 4849 | 0 |
| UNKNOWN | 4782 | 5 |
| habitat | 4076 | 7 |
| tropik | 1688 | 2 |
| rainforest | 34 | 0 |
| goss | 3 | 0 |
| theone | 0 | 0 |

The One has no row in this catalog. That is an empty library, not a guessed count.

Beta :8788 as Creative Director (`ASG-HAIKAL-CD-1`, `ROLE-GGV-CREATIVE-DIRECTOR`, source `org_assignments`), not an owner bypass. `python3 scripts/tests/test_content_engine_nas_library_round3.py`:

```
PASS  production pid unchanged before — 15975
PASS  session is creative director — {'id': 'ASG-HAIKAL-CD-1', 'role': 'ROLE-GGV-CREATIVE-DIRECTOR', 'source': 'org_assignments'}
PASS  historical keyword search hits — q=Atrium ava matched=1 cards=1
PASS  photo results — 1
PASS  video results — 48
PASS  brand switching changes the library — habitat=1676 atrium=17010
PASS  photo preview — image/jpeg
PASS  video preview — video/quicktime
PASS  individual download — attachment; filename="Atrium ava.jpg"
PASS  multi-select zip — status=200 bytes=9568126
PASS  smart upload received on NAS — _Imports/Wolf-Library/atrium/RAW/2026/atrium_RAW_image_wolf-test-upload_wolf-test-upload-20260926224425-jpg_20260926_001.jpg
PASS  upload is searchable in the library — 17
PASS  uploaded file is on the NAS path — /Volumes/01-Media-Library/_Imports/Wolf-Library/atrium/RAW/2026/atrium_RAW_image_wolf-test-upload_wolf-test-upload-20260926224425-jpg_20260926_001.jpg
PASS  staff_ready stays false
PASS  production pid unchanged after — 15975
EXIT: SUCCESS PASS=19 FAIL=0
```

NAS path of `WOLF-TEST-UPLOAD-20260926224425.jpg`:

`/Volumes/01-Media-Library/_Imports/Wolf-Library/atrium/RAW/2026/atrium_RAW_image_wolf-test-upload_wolf-test-upload-20260926224425-jpg_20260926_001.jpg`

Ports after the run: :8787 listener pid 15975. :8788 listener pid 47662. Indexer pid file removed after caught_up.

## STAFF READY?

No. `staff_ready` is false on the catalog counts, the truth file, and the Beta library response. 4787 rows are still `UNKNOWN` (unsorted imports, Tampah Reserve, staff document folders, and other trees that are not one of the eight brands). 124 files have no thumbnail. Haikal has not used the desk.

## HUMAN COMMISSIONED?

NO

## BLOCKERS

- The One: zero files in `nas_index`. Nothing in the manifest mapped to that brand.
- `UNKNOWN`: 4787 rows. Folder evidence was not deterministic. They stay out of the eight brand libraries.
- 124 genuine preview/hash failures in `state/nas-estate/exceptions.json`. They did not stop the other 63246 rows.
- This catalog is the discovery manifest (63370 rows). It is not a claim that every file on the NAS was visited.

## NEXT HUMAN TEST

Haikal, on Beta :8788, signed in as himself. Checklist: `docs/wolf/sprint7/HAIKAL-ROUND3-CHECKLIST.md`. He decides whether the library is usable. This run does not.

## FOUNDER DEPENDENCY

- Rechecking a stale `missing_file` row and rendering the rest of the library: AUTOMATE. No Matt step.
- Thumbnail and hash exceptions: AUGMENT. The exceptions list is there; the other rows do not wait on a person.
- `UNKNOWN` rows and the empty The One library: RETAIN for a person who knows which folders are which brand. Not a new Matt login, and not keyed on a person name.
- Share mounted at `/Volumes/01-Media-Library`: RETAIN as machine setup. A down share is retried, not marked deleted.
- Calling the desk staff-ready: RETAIN for Haikal. Not Matt.

No new Matt dependency was added to get this run green.

GATE: CONTENT ENGINE — NAS MEDIA ESTATE READY FOR HAIKAL ROUND 3

RESULT: PASS
