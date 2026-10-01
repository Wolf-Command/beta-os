# Pack 4 — Habitat shoot card → comment → tick → queue

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. No staff clicked the page. Haikal upload retest stays OPEN. This pack did not write upload state.

## Which cycle, and why

Habitat. The V1 file `dashboards/data/content-plans/habitat-2026-09-28-11.json` has `cycle_start` 2026-09-28 and `cycle_end` 2026-10-11, which contains 2026-10-01. Atrium has a file with the same window. Beta `content_plans` rows are Habitat too, and their `period_end` is 2026-09-27, so those are the previous fortnight. Habitat is also the brand the Beta publish gate already locks. The current file is read `mode=ro` from the V1 path. It is not a copy on the Beta disk. Its six feed posts have blank titles, and those titles were not filled in. The ticked card is story `s2`, whose file title is `Book a site tour with Matt`.

## Chain

Verified 2026-10-01 on `http://127.0.0.1:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`.

| Path | Result |
|---|---|
| `GET /api/content/tick-draft` | 200. Habitat, 2026-09-28 → 2026-10-11, 6 posts, 28 stories, 34 cards. `full_tree_indexed` false. `haikal_upload_retest` OPEN. |
| `GET /content/tick-draft` | 200 HTML. |
| `POST /api/content/tick-draft/comment` | 200. Note 1 on `s2`: "Tour story already says book a site tour. No new caption invented." |
| `POST /api/content/tick-draft/apply` | 200. Applied that comment. `amanda_session` false. `cycle_file_written` false. |
| `POST /api/content/tick-draft/tick` | 200. Queue `MISA-CBA83917AE23`, state `QUEUED`, reason `metricool_write_blocked`, title `Book a site tour with Matt`, publish `OFF`, network false. |
| Second tick | 200. `idempotent` true. Same id. |
| `POST /api/content/tick-draft/publish` | 405 `publish_off`. |
| `GET /api/health` `:8788` and `:8787` | 200. |

Metricool write is fail-closed (`BETA_METRICOOL_WRITE_ENABLED` false). No draft request was sent. The Misa queue row is the fallback. An injected draft client in the test records `METRICOOL_DRAFT` with publish `OFF`. A client that sets `published` true is refused and does not queue.

## Library

Assets table count 48. `habitat_RAW_video_habitat-vibe_workers_20260730_001.mov` is `library`. `/Volumes/01-Media-Library/Brand-Assets/GGV/logos/goss-group-logo.png` exists and is `nas_only` (one file stat). `pack4-not-a-real-file.mov` is `not_in_library`. `tree_walked` false. `full_tree_indexed` false. The 38091 NAS count was not re-walked.

## Tests

`scripts/tests/test_content_tick_draft_pack4.py`: 22 passed, 0 failed. The cycle file mtime was unchanged.

## Left undone

The other five brand boards. Metricool publish. A signed Amanda session. Editing the V1 cycle file. Filling the blank feed titles. Haikal upload retest. The Misa desk page. `staff_ready`.

## NEXT — Pack 1, not started

Owner cockpit. Pack 4 finished clean, so the next pack is Pack 1 rather than Pack 5. Atrium finance screens stay behind the SoD lock until that cockpit pass is done.
