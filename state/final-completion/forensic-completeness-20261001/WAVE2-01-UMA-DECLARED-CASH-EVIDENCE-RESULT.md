# Wave 2.01 — Uma declared cash

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. No till figure was written. Prod `:8787` was health-checked and not restarted.

## Night close

Source: `catalog/content_library.sqlite` `venue_daily_closes`, opened read-only. The catalog mtime did not change.

`VDC-25a3123a-3e26-43db-8085-10c6f208bbcd` is still `DATA_CAPTURED` for `2026-09-30`, venue `BZG-UMA`. `declared_cash_amount` is null. `declared_cash_evidence_id` is null.

Today's close `VDC-3353351f-3234-4f7d-acf0-a63e0e176114` is still `OPEN` for `2026-10-01`, with the same two fields null. An OPEN close is not a state the attach function accepts.

## Count

Source: Alchemist `data/alchemist.db` `cash_count`, opened read-only. The file mtime did not change. Row count is 0. Count state UNAVAILABLE.

The attach function raises `invalid_amount` when the amount is missing, and it does that before it opens the catalog. It was not called with a number. A zero till was not written.

## What was not used as the till

ESB totals already stored on the night close: `cash_from_payments` 2610000, label `ESB_CASH_FROM_PAYMENTS`, provenance `ESB payment lines (salesPayments) — not settlement`. `copied_to_declared_cash` is false. Finished count 50 and grand total 15140000 stay the sales snapshot.

Receipt `EVD-372162c1-d0ac-42a6-b5f3-5959c11f4621` is a receiving document. Petty photo `EVD-9498bb75-294c-4924-b30b-8cef0cab5351` is a Transport photo. Neither was attached to the close.

## Authority

`org_authority_limits` count is 0. `within_authority` for Matt / `work.complete` / the existing petty amount returns `higher_approval_required`. `matched_limit` is null. No limit row was written. `core_approval_requests` stays 1.

## HTTP

Verified 2026-10-01 on `:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. No Cloudflare JWT was presented. Auth mode was not changed.

| Path | Result |
|---|---|
| `GET /api/bzg/uma-blu/declared-cash` | 200, FAIL_CLOSED, evidence null, cash_count 0 |
| `GET /uma/declared-cash` | 200, four tiles, none start open |
| `POST /api/bzg/uma-blu/declared-cash` | 405 `writes_off` |
| `GET /api/health` `:8788` and `:8787` | 200 |

The page script loads the JSON. A browser click-through was not done.

## Tests

`scripts/tests/test_uma_declared_cash_wave2_01.py`: 16 passed, 0 failed.

## Left undone

A physical till count. An evidence row on the close. A filed close. `staff_ready`.

## NEXT — Wave 2.02, not started

Housekeeping and room status, register row `need.housekeeping`. Not started.
