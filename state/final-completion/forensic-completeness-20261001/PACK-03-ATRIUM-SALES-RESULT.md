# Pack 3 — Atrium sales desk

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. No staff clicked the page.

Verified 2026-10-01 from a `mode=ro` open of `~/.openclaw/workspace/wolf-system/atrium/atrium_sales.sqlite` and from `GET http://127.0.0.1:8788/api/amg/sales-desk` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. Formulas are `wolf-system/scripts/dash_data.py` (ladder, deal labels, tax ceiling 4,800,000,000). The sqlite was not written (mtime and size unchanged; `PRAGMA query_only` rejects INSERT). Prod `:8787` health stayed 200. Auth mode was not changed.

## What a named path can do

| Path | Result |
|---|---|
| `GET /api/amg/sales-desk` | 200. Units 88, leads 570, payments 399. 14 view ids. `staff_ready` false. `writes` false. |
| `GET /api/amg/sales-desk/<view>?limit=40` | 200 for overview, milestones, payments, newsale, inventory, deals, leads, comms, cv, payables, tax, vendors, commonarea, exceptions. Each total matches the index. At most 40 rows. |
| `GET /amg/sales-desk` | 200 HTML. Tabs call the API. Occupancy and Kuta start collapsed. |
| `POST /api/amg/sales-desk` | 405 `writes_off`. |
| `GET /api/health` `:8788` and `:8787` | 200. |

View totals from that GET: overview 16 KPI facts, milestones 4, payments 399, newsale 13 available, inventory 88, deals 8, leads 570, comms 68, cv 5, payables 17, tax 5, vendors 27, common area 85, exceptions 61.

Exceptions: the view is `resolved=0` (61). The table also holds 88 rows including resolved. The 88 are not reported as open exceptions.

A lead row on the wire (`id` 1, name Mike Cannon, source Walk In) matches the sqlite. Email, phone, and notes are not on the wire. Vendor bank accounts are not on the wire.

New sale lists the 13 Available units and the fields a sale would record. It does not POST.

## Occupancy — two questions, not one number

Yanolja last-read `2026-10-01T07:16:15+08:00`, source `yanolja_last_read`: `89% · 13 vacant / 114 rooms` (`occupancy_pct` 88.6, `rooms_vacant` 13, `rooms_total` 114). Guests null. In-house UNKNOWN. Arrivals UNKNOWN. ADR and RevPAR are null.

V1 `dashboards/data/master.status.json` atrium tile, same day: `1.75% occ`. Labeled on the card as a different question. `merged_pct` is null.

Live pulse tile `atrium_occ` href is `/amg/sales-desk#occ`. That href edit is in the already-untracked live `scripts/core/owner_pulse_ro.py`. This commit does not add that module.

## Kuta tonight — same desk

`ops_kuta_rates_ro` status official: night `2026-10-01 → 2026-10-02`, generated `2026-10-01T08:18:01+08:00`, headline `Montana Family Double Queen Room RO IDR 1.274.000 · cheaper than 2jt`, 13 official rows, 12 shown. Booking false. Leaf `/kuta-rates` remains. Live pulse `kuta_rates` href is `/amg/sales-desk#kuta` via the same untracked module.

## Tests

`scripts/tests/test_amg_sales_desk_pack3.py`: 36 passed, 0 failed. The page was not human-clicked.

## Left undone on purpose

Housekeeping. Guest-stay middle (pack 7). HR. Exit Report. Wolf Intelligence. Recording a sale. The separate inventory board (`atrium-inventory.html`). Atrium finance screens. `staff_ready`.

## NEXT — Pack 4, not started

Content shoot → tick → draft. One brand (Habitat or Atrium, the one with a current cycle file). Tick creates a Metricool draft or a Misa queue item when the API fails. Library lookup must say when the file is among the 48 assets and when it is only on the NAS. WRITE to publish stays off.
