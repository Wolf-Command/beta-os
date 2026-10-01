# Pack 5 — Atrium finance screens under separation of duties

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. The books file was opened read-only and its mtime did not change. No Xero write. Payroll distribution was not opened. Prod `:8787` was health-checked and not restarted.

## What was read

Source: `/Users/wolfterminal/atrium-finance/data/beta/atrium.sqlite`, `books_slot_meta` legal entity `ENT-AMG`, `shell_kind` live, `staff_ready` flag 0.

| Screen | State | Read |
|---|---|---|
| Night audit | PARTIAL | 2 `revenue_transactions`, both source Manual, date 2026-09-30, amounts 5750000 and 1000000. Not a PMS night audit. |
| Flash | PARTIAL | No GM flash generated. ADR empty. Rooms sold empty. |
| Cash | UNKNOWN | No uploaded statement. Bank balance null. One books spending row (3000000, Procurement) is not a match. No bank feed. |
| Close | PARTIAL | 13 journals, 4 POSTED, 3 APPROVED, 6 ARCHIVED. Tax periods closed: 0. Historical import `NOTHING_AUTHORITATIVE`, row count 0. Month not closed. |
| Owner pack | PARTIAL | `report_config` id 1 is present. 0 owner email drafts. Nothing exported. The config JSON was not rendered as a statement. |
| Payroll | BLOCKED | `service_charge_cycles` count 0. HR boundary left closed. |

## Separation of duties

The posted journal `JRN-ATRIUMSOD1B-COMM1` has preparer `PERS-ZENITALFATHAN` and approver Zayen. `JRN-ATRIUMSOD1B-SELF` is ARCHIVED with no approver.

A temp review store, not the books file: Zenit submits an AMG close review with no amount. Zenit approving it returns `self_approval_denied`. Amanda (`PERS-AMANDA`) approving it returns `entity_denied`. Zayen approving it returns APPROVED, `posted` false, `xero_write` false. Zayen submitting the same review for `ENT-GGV` returns `entity_denied`.

Seat check, same permissions as the repaired isolation: Zayen AMG yes, BZG yes, GGV no. Amanda AMG no, GGV yes.

## HTTP

Verified 2026-10-01 on `:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. No Cloudflare JWT was presented.

| Path | Result |
|---|---|
| `GET /api/amg/finance/screens` | 403 `missing_auth` |
| `GET /amg/finance/screens` | 403 `missing_auth` |
| `POST /api/amg/finance/screens/xero` | 403 `missing_auth` |
| `POST /api/amg/finance/screens/payroll` | 403 `missing_auth` |
| `GET /api/amg/finance/no-such` | 404 |
| `GET /api/amg/sales-desk` | 200 |
| `GET /wolf` | 403 `missing_auth` |
| `GET /api/health` `:8788` and `:8787` | 200 |

The screen route is the finance guard. The page was not clicked. Auth mode was not changed.

## Tests

`scripts/tests/test_amg_finance_screens_pack5.py`: 27 passed, 0 failed.

## Left undone

The other Atrium finance shells (command centre, procurement, assets, payment run, tax, accounting core, PSAK, master data, handoff). A PMS night audit. An uploaded statement match. An exported owner pack. Xero. Payroll. GGV nota. `staff_ready`.

## NEXT — Pack 6, not started

GGV nota. Guest stay stays Pack 7. This pack did not open GGV.
