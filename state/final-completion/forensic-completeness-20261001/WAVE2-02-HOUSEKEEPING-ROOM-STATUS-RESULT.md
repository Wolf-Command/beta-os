# Wave 2.02 — Housekeeping and room status

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. No clean, dirty, or inspected count was written. Prod `:8787` was health-checked and not restarted. Bookings was not enabled.

## Inventory is not a status

Source: `state/yanolja/last-read.json`, kind `Inventory+RoomInfo`, written `2026-10-01T07:16:15+08:00`. Display `89% · 13 vacant / 114 rooms`. Source label `Yanolja Inventory+RoomInfo`. `used_as_housekeeping` is false. The file mtime did not change.

## Room status

Clean, dirty, inspected, and out of order are null. `derived_from_occupancy` is false. State UNKNOWN.

In-house room status on the same last read: `ok` false, HTTP 200, error codes `502` and `Request Type is missing`, `row_count` null. That null is not zero rooms. State UNKNOWN.

## Probes

Source: `state/yanolja/guest-depth-probe-20261001c.json`, probed `2026-10-01T07:31:35+08:00`. The file mtime did not change.

Six paths, each HTTP 404, `has_roomlist` false, state UNAVAILABLE:

- `/pmsinterface/getRoomStatus.php`
- `/pmsinterface/getInhouseRoomStatus.php`
- `/pmsinterface/housekeeping.php`
- `/booking/reservation_api/getRoomStatus.php`
- `/booking/reservation_api/housekeeping.php`
- `/channelbookings/housekeeping.php`

`roomlist_n` 0 on a 404 body is not a status count.

There is no `day_objects` table in the Beta catalog. No stored housekeeping board was read.

## Bookings

The Bookings endpoint on the last read is denied, error `302` / `Unauthorized Request. Integration is not allowed`. `bookings_enabled` is false. No write was attempted.

## HTTP

Verified 2026-10-01 on `:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. No Cloudflare JWT was presented. Auth mode was not changed.

| Path | Result |
|---|---|
| `GET /api/amg/housekeeping` | 200, UNAVAILABLE, clean/dirty/inspected null |
| `GET /amg/housekeeping` | 200, four tiles, none start open |
| `POST /api/amg/housekeeping` | 405 `writes_off` |
| `GET /api/health` `:8788` and `:8787` | 200 |

The page script loads the JSON. A browser click-through was not done.

## Tests

`scripts/tests/test_amg_housekeeping_wave2_02.py`: 14 passed, 0 failed.

## Left undone

A room list with clean, dirty, or inspected. An in-house guest list. Bookings. `staff_ready`.

## NEXT — Wave 2.03, not started

CRM identity, register row `need.crm.identity`. Not started.
