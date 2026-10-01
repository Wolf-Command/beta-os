# Wave 2.05 — Content learn-back

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. No learn-back row was written into a brief. Metricool write stayed off. Prod `:8787` was health-checked and not restarted.

## Performance store

Source: `catalog/content_library.sqlite` `performance_records`, opened read-only. Count 1103. Every row is `external_system` metricool, `data_lane` operational.

| Brand | Rows |
|---|---|
| tropik | 276 |
| selo | 240 |
| umablu | 210 |
| atrium | 198 |
| habitat | 179 |

Engagement is null on 1012 rows. Published from `2026-07-15T23:02:34Z` through `2026-09-14T09:02:15Z`. Fetched from `2026-09-15T07:39:08+08:00` through `2026-09-15T07:45:19+08:00`. Captions and permalinks were not copied. The catalog mtime did not change.

This count is a history store. It is not a learning loop.

## Previous snapshots

`planning_context_snapshots` count 6, all `habitat`, plan ids 4 through 9. Each snapshot lists 6 `performance_record_ids`. Those plans are period `2026-09-14` → `2026-09-27`. Catalog plans with `period_start` on or after `2026-09-28`: 0.

## Current brief

Source: `dashboards/data/content-plans/habitat-2026-09-28-11.json` on the V1 tree, read-only. Brand habitat. Cycle `2026-09-28` → `2026-10-11`. 6 posts, 28 stories. Updated `2026-09-28T08:57:03+08:00`. The file contains no `performance_record` id. The intro names a Metricool snapshot pulled `2026-08-21T10:26:50+08:00` in prose. That sentence is not a row join. The file mtime did not change.

## Publish path

`content_misa_queue` has 1 row, state `QUEUED`, reason `metricool_write_blocked`, publish `OFF`. That is the Pack 4 tick fallback. It is not a learn-back row.

`BETA_METRICOOL_ENABLED` is true. `BETA_METRICOOL_WRITE_ENABLED` is false. No Metricool request was sent.

## Learn

State UNAVAILABLE. `fed_into_current_brief` false. `rows_written` false.

## HTTP

Verified 2026-10-01T22:18:23+08:00 on `:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. No Cloudflare JWT was presented. Auth mode was not changed.

| Path | Result |
|---|---|
| `GET /api/content/learn-back` | 200, learn UNAVAILABLE, brief has no performance id, write false |
| `GET /content/learn-back` | 200, four tiles, none start open |
| `POST /api/content/learn-back` | 405 `writes_off` |
| `GET /api/health` `:8788` and `:8787` | 200 |

The page script loads the JSON. A browser click-through was not done.

## Tests

`scripts/tests/test_content_learn_wave2_05.py`: 11 passed, 0 failed.

## Left undone

A join from a published result into the next brief. A Metricool write. `staff_ready`.

## NEXT — Wave 2.06, not started

Month-end shareholder pack honesty, register row `need.monthend.shareholder`. Not started. A later pass may be a read-only shell. No P&L was invented here.
