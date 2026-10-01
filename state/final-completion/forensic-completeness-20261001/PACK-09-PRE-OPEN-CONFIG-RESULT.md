# Pack 9 — Pre-open config

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. No sales, till, covers, or close figures were invented. Prod `:8787` was health-checked and not restarted.

## Registry

Source: `catalog/content_library.sqlite` `org_outlet_registry`, opened read-only. The catalog mtime did not change.

| Outlet | Status | Board title | Stored display name | Close rows |
|---|---|---|---|---|
| OU-BZG-RAIN-POOL | PRE-OPENING | Pool Bar | Pool Bar | 0 |
| BZG-MERAH | PRE-OPENING | Merah | Merah | 0 |
| BZG-ROOF | PRE-OPENING | Rooftop | Rooftop | 0 |
| BZG-RS | PRE-OPENING | Room Service | Room Service | 0 |
| BZG-CAT | PRE-OPENING | Catering | Catering | 0 |
| BZG-RAIN | PRE-OPENING | Blu Zone Restaurant | Rainforest | 0 |

`BZG-UMA` stays OPEN. Its two closes were not used as a pre-open close.

Pool Bar's parent outlet is `BZG-RAIN`. The parent board title is Blu Zone Restaurant. The parent stored display name stays Rainforest.

## Name

PARTIAL. `CLAUDE.md` B3 names **Blu Zone Restaurant** and says Rainforest Restaurant is dead. That is the board title on `/bzg/pre-open`.

`org_outlet_registry.display_name` for `BZG-RAIN` is still Rainforest. `state/brand-config.json` `brands.Rainforest.label` is still Rainforest. Those stored labels were not overwritten. The page title is "Pre-open outlets".

## Close template

BLANK. `inserted` is false. `business_date`, sales, covers, till, declared cash, and ESB totals are null. No `venue_daily_closes` row was written. `close_count` 0 is a read of those six ids, not a zero-sales day.

Sales, till, and covers on the payload are null. Live operating numbers for these outlets are UNKNOWN.

## HTTP

Verified 2026-10-01 on `:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. No Cloudflare JWT was presented. Auth mode was not changed.

| Path | Result |
|---|---|
| `GET /api/bzg/pre-open` | 200, six cards, title Blu Zone Restaurant, sales null, staff_ready false |
| `GET /bzg/pre-open` | 200, six tiles, none start open |
| `POST /api/bzg/pre-open` | 405 `writes_off` |
| `GET /api/health` `:8788` and `:8787` | 200 |

The page script loads the JSON. A browser click-through was not done.

## Tests

`scripts/tests/test_preopen_config_pack9.py`: 19 passed, 0 failed.

## Left undone

An operating desk for any of the six. A real close. Sales, till, and covers. Overwriting the stored Rainforest label. `staff_ready`.

## NEXT — Pack 10, not started

Approvals and evidence. Authority limits are 0. This is the gate other packs call, not a new scoreboard. Pack 10 was not started.
