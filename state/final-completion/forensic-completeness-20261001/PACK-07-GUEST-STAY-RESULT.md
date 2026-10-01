# Pack 7 — Guest stay

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. No occupancy figure and no guest count was invented. Bookings were not written. Housekeeping was not opened. Prod `:8787` was health-checked and not restarted.

## Stay

Source: `state/yanolja/last-read.json`, kind `Inventory+RoomInfo`, written `2026-10-01T07:16:15+08:00`, hotel `63221`.

The stay card is PARTIAL. Display `89% · 13 vacant / 114 rooms` (`occupancy_pct` 88.6, `rooms_vacant` 13, `rooms_total` 114, `rooms_occupied` 101). Guests null. In-house UNKNOWN. Arrivals UNKNOWN. ADR and RevPAR null.

It opens `/amg/sales-desk#occ`. The V1 master tile value `1.75% occ` stays a different question and is not merged. Pack 3’s occupancy question remains `vacant_versus_rooms`.

## Pre-arrival

UNAVAILABLE. No desk. ArrivalList in the same last-read, probed `2026-10-01T07:30:53+08:00`, error codes `105` / `From Date is missing`, `row_count` null. Null is not zero guests.

`n8n-templates/02-amg-pre-arrival.json` exists and is not an operating workflow.

## Post-stay

UNAVAILABLE. No departure folio. No desk.

`n8n-templates/05-amg-post-stay-review.json` exists and is not an operating workflow.

## What was not a guest book

`wolf-system/state/reservations.db` has 1 row: venue Uma Blu Cafe, party size 4, `2026-05-21T04:00:00`, status confirmed. Name, phone, and email were not copied onto the wire. That row is a cafe reservation, not an Atrium stay, and it is not “no guests”. Hotel reservation history is UNAVAILABLE. The file mtime did not change.

Bookings endpoint is denied (`302` / integration not allowed). `bookings_dated` is `ok` true with `row_count` null, `writable` false, `write_attempted` false. That probe is not a guest list. Write stays off.

In-house room status error codes are `502` / `Request Type is missing`, `row_count` null. The stored last-read note also says the in-house kiosk returned 500. Neither number is a guest count.

## Housekeeping

OUT_OF_SCOPE. Later pack. This pack did not open it.

## HTTP

Verified 2026-10-01 on `:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. No Cloudflare JWT was presented. Auth mode was not changed. The route is the same read-only wall as the sales desk, not a weakened JWT.

| Path | Result |
|---|---|
| `GET /api/amg/guest-stay` | 200, stay PARTIAL, guests null |
| `GET /amg/guest-stay` | 200, three tiles, none start open |
| `POST /api/amg/guest-stay` | 405 `writes_off` |
| `GET /api/amg/sales-desk` | 200 |
| `GET /api/health` `:8788` and `:8787` | 200 |

The page script loads the JSON. A browser click-through of the three tiles was not done.

## Tests

`scripts/tests/test_amg_guest_stay_pack7.py`: 25 passed, 0 failed.

## Left undone

A hotel reservation book. An in-house guest list. A pre-arrival desk. A departure folio. Housekeeping. Bookings write. `staff_ready`.

## NEXT — Pack 8, not started

Recipe variance. Theoretical versus actual for Uma recipes that already have lines. ESB product mix has to be real or the variance stays UNKNOWN. Pack 9 pre-open config was not started.
