# NAS indexer repair — 26 Sep 2026

Beta catalog only. Nothing in a NAS media tree was moved, renamed, deleted, or written. Production :8787 was not touched. `staff_ready` stays false. This is not a claim that the whole NAS is complete.

## Before

Owner counts at `2026-09-26T06:48:47+08:00`, phase `caught_up`, manifest line 63337.

| | |
| --- | --- |
| catalog rows | 63370 |
| FAILED | 41886 |
| HASHED | 21472 |
| SEARCHABLE | 0 |
| blank `index_state` | 12 |

Fail reasons on the FAILED rows: `missing_file` 40564, `missing_file_at_hash` 1292, `thumb_failed` 25, `thumb_timeout` 5.

| brand | FAILED | HASHED |
| --- | ---: | ---: |
| atrium | 26516 | 6137 |
| umablu | 8393 | 53 |
| SHARED_STOCK | 3586 | 1263 |
| habitat | 3220 | 807 |
| UNKNOWN | 162 | 5151 |
| selo | 7 | 6471 |
| tropik | 2 | 1590 |

UNKNOWN also had 12 rows with a blank state.

## Sample

50 FAILED rows whose reason starts with `missing_file`. Seed 26. Stratified by the first four path segments, then truncated to 50, so the sample follows the largest trees (atrium, umablu, habitat, SHARED_STOCK). Each path was `os.stat`'d as stored, as NFC, as NFD, and after a stale-mount remap (`00-Editing-Workspace` / `-1` / `-2` → `-3`, `02-Stock-Assets` → `02-Stock-Assets-1`).

Result: **50 / 50 are regular files on the raw path.** NFC, NFD, and the remap string were the same hit. No sample needed a different variant. Ids: 29616, 11772, 26739, 11851, 19299, 24814, 22955, 6988, 9319, 30567, 30177, 20767, 6496, 29055, 27522, 25556, 21602, 10752, 25951, 19206, 13073, 29630, 18535, 28630, 11746, 30894, 27820, 6072, 26974, 12412, 9854, 9369, 35192, 39561, 38013, 37613, 35636, 32149, 32142, 36453, 33682, 39992, 40382, 42842, 40234, 42104, 62529, 62763, 62369, 61355.

Checked across every `missing_file*` row, not only the sample:

| check | result |
| --- | --- |
| failed paths on a stale stub (`00-Editing-Workspace` without `-3`, or `02-Stock-Assets` without `-1`) | 0 |
| manifest lines that are not 8 tab columns | 0 of 63337 |
| paths that are not absolute `/Volumes/...` | 0 |
| failed paths whose NFC form differs | 22, and the raw path is already a regular file |
| failed paths containing `%` | 4; raw `stat` is a file. Unquote would miss 2 of them, because `%` is literal in the filename |

## Root cause

`Path.is_file()` was treated as a permanent `missing_file`. That call returns false for a missing path and for any `OSError`, and the row was then left FAILED, so it never reached `SEARCHABLE`.

The marks are a time window, not a bad prefix. At `2026-09-26T01:36:08` the thumb pass was still hashing neighbours in one folder (`IMG_1493.MOV` HASHED, `IMG_1494.MOV` thumb_failed, `IMG_1495.MOV` and the following ids `missing_file`). The same split happens again where the volume answered again (`Green-Habitat-Garden.jpg` FAILED, `Green-Habitat-Vibe.jpg` HASHED, same directory). Failures then ran through a contiguous id range across Atrium, Uma Blu, and Habitat, and a second burst at `06:48:26` marked the stock-library tail. Re-stat the next morning finds those same absolute paths as regular files, with sizes matching the catalog.

`SEARCHABLE` stayed 0 for a second reason. Hashing only accepts `SEARCHABLE`, then moves the row to `HASHED` in the same loop, and hashing ran before that loop's new thumbs were promoted. Library search already includes `HASHED`, which is why atrium (6137), selo (6471), and habitat (807) already matched on the hashed subset. The false `missing_file` rows never entered that path.

## Repair

`resolve_media_path` tries the stored path, NFC, NFD, a single URL-unquote, a stale-mount remap, a relative join onto the live read roots, and a read-only same-directory NFC name match. The raw path wins when it is already a file, so a literal `%` is not rewritten. A transient stat error (`EIO`, `ESTALE`, timeouts, and the same class) leaves the row `INDEXED` for retry. A directory is `missing_file:not_a_regular_file`. A path that still does not resolve stays FAILED as `missing_file:not_found`.

Each start re-queues FAILED and blank rows whose file resolves, back to `INDEXED`. A second pass does not insert a row. Duplicate path clashes are recorded and neither row is deleted.

The enrich order is now thumb, then promote `THUMB_PREVIEW_READY` to `SEARCHABLE`, then hash. A row is searchable before it is hashed. Library search on Beta returns `SEARCHABLE` and `HASHED` rows for atrium, selo, and habitat.

## After

Requeue at `2026-09-26T08:34:01+08:00`. Every failed and blank row resolved to a regular file. `still_missing` 0. `transient` 0. `requeued` 41898 (41886 FAILED + 12 blank). Catalog row count stayed 63370. Duplicate candidates stayed 22375. No NAS file was deleted.

| | before | after requeue |
| --- | ---: | ---: |
| catalog rows | 63370 | 63370 |
| FAILED | 41886 | 0 |
| HASHED | 21472 | 21472 |
| INDEXED | 0 | 41898 |
| SEARCHABLE | 0 | 0 |

`SEARCHABLE` is still 0 at this instant because those 41898 rows are `INDEXED`, waiting for the thumb pass. The enrich order promotes them to `SEARCHABLE` before hashing. The detached indexer does that next. `staff_ready` is false. `full_nas_complete` is false.

| brand | HASHED | INDEXED |
| --- | ---: | ---: |
| atrium | 6137 | 26516 |
| selo | 6471 | 7 |
| habitat | 807 | 3220 |
| umablu | 53 | 8393 |
| tropik | 1590 | 2 |
| SHARED_STOCK | 1263 | 3586 |
| UNKNOWN | 5151 | 174 |

