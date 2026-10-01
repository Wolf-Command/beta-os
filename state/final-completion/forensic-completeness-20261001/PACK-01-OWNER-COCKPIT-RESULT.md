# Pack 1 — Owner cockpit

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. Nobody clicked the page. Finance separation of duties was not opened. Prod `:8787` was health-checked and not restarted.

## What the home is

`GET /api/owner/cockpit` on `:8788` returns the 10 live pulse cards, then the questions that pulse dropped, then a personal rail. `GET /owner/cockpit` is a read board of that JSON. Tiles are closed until opened.

`GET /wolf` and `GET /owner-empire-pack` still call `_require_owner_empire`. Without a Cloudflare JWT both returned **403** `missing_auth`. Auth mode was not changed.

## Cards

Verified 2026-10-01 on `http://127.0.0.1:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`.

| Card | State | What was read |
|---|---|---|
| Pulse, 10 cards | kept | UNKNOWN lines left in place. Occupancy href `/amg/sales-desk#occ`. Kuta href `/amg/sales-desk#kuta`. Uma href `/bzg/uma-blu#closes`. |
| Command Brief | PARTIAL | Vault `Brief-2026-10-01.md` is present. Body not copied. V1 "Ready" stamp not used. No Beta brief desk. |
| R2 gap | PARTIAL | `offbox-backup.json` verdict NO-GO at 2026-10-01T16:49:25+08:00. `r2-sync-state.json` last gap 2026-08-15 still records `objects_still_missing` 0. That zero is not a current absent count. Not re-measured. |
| System | PARTIAL | `daemon-status.json` has 14 records, each status ok. No job id. Not reported as Beta 14/14 green. |
| Team asks | EMPTY | `wolf-desk/tasks.json`: 0 open `bucket=ask` rows of 89 tasks. Titles not copied. No answer-in-place rail. |
| Peaches | PARTIAL | 57 lines in V1 `peaches-desk/threads.jsonl`, newest 2026-09-16T16:56:31+08:00. Text not copied. Beta `threads.jsonl` absent. Not LIVE. |
| Content | PARTIAL | Opens `/content/tick-draft`. Habitat 2026-09-28→2026-10-11. Queue `MISA-CBA83917AE23`. Publish OFF. Haikal retest OPEN. |
| Money | PARTIAL | Value null. No figure read. |
| Fitness | personal PARTIAL | Pulse loader still stamps the tile LIVE. The personal rail does not. Not staff primary. |
| Trading | personal PARTIAL | `/owner/trading`. Paper. `live_broker` false. Holdings not copied. Not 14 cards. |

Staff primary is the 10 pulse cards without fitness (9). Fitness and trading are the personal rail.

## HTTP

| Path | Result |
|---|---|
| `GET /api/owner/cockpit` | 200. `staff_ready` false. pulse 10, staff primary 9, restored 7. |
| `GET /owner/cockpit` | 200 HTML. Not clicked in a browser. |
| `POST /api/owner/cockpit` | 405 `cockpit_read_only`. |
| `GET /wolf` | 403 `missing_auth`. |
| `GET /owner-empire-pack` | 403 `missing_auth`. |
| `GET /amg/sales-desk` | 200. |
| `GET /content/tick-draft` | 200. |
| `GET /bzg/uma-blu` and `GET /api/bzg/uma-blu/today` | 403 `missing_auth`. The Uma card points at the real desk. The JWT wall was left closed. |
| `GET /owner/fitness` and `GET /owner/trading` | 200. |
| `GET /api/health` `:8788` and `:8787` | 200. |

## Tests

`scripts/tests/test_owner_cockpit_pack1.py`: 22 passed, 0 failed. The R2, off-box, daemon, task, and thread files were not rewritten.

## Left undone

Needs-you, calendar writes, read/view, edits, reports, overnight coder, and the mission meter. HR. A rebuilt Command Brief. A fresh R2 measurement. A fault that opens a job. Answering an ask on the home. A Beta Peaches thread desk. Money. The empire page behind Cloudflare. `staff_ready`.

`owner_pulse_ro.py` stays untracked. The cockpit calls it. This commit does not add that file.

## NEXT — Pack 5, not started

Atrium finance screens under separation of duties. Pack 6 GGV nota stays the alternative. This cockpit did not block Pack 5.
