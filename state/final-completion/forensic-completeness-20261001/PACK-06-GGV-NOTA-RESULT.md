# Pack 6 — GGV nota

Eng proof only. `staff_ready` stays false. Not HUMAN_PROVEN. Capture was proved on a catalog copy. The live catalog was not written. Issue stayed blocked so the built-in seed `067A` was not consumed. No Xero write. Atrium books were not opened. Prod `:8787` was health-checked and not restarted.

## Honesty

| Fact | State |
|---|---|
| Capture | Eng-proved on a catalog copy for `PERS-AMANDA` |
| Live `ggv_notas` / `ggv_uploads` / `ggv_invoices` / `ggv_vendors` | 0 / 0 / 0 / 0 after the proof |
| Invoice sequence | `ENT-GGV` format `{n:03d}A`, `next_value` 67. Rendered seed label `067A`. `allocated` false |
| Issue | Blocked. No number assigned |
| Xero | Not called |
| Supplier | Canonical spelling `M-Mart` from `scripts/ggv_nota_supplier_aliases.json`. Merge script was not run |
| Amount | Not confirmed. Stored amount is null. Workflow `needs_review` |
| AMG | Capture with `entity_id` ENT-AMG returns `entity_denied`. Amanda `atrium.board.read` on ENT-AMG is false |
| Zayen | `finance.nota.create` and `finance.nota.read` on ENT-GGV are false |
| Phone commission | Open. Matt and Amanda phone commission is not done |
| NAS | The slip was written under a temp media root, not `/Volumes/01-Media-Library` |

The copy row is `ENT-GGV`, invoice number empty, amount null. That copy was deleted with the test temp directory. Live rows stayed 0.

## HTTP

Verified 2026-10-01 20:53 WITA on `:8788` after `launchctl kickstart` of `net.wolfcommand.serve-beta`. No Cloudflare JWT was presented. Auth mode stayed `cloudflare_access`.

| Path | Result |
|---|---|
| `GET /api/ggv/finance/pack6` | 403 `missing_auth` |
| `POST /api/ggv/finance/pack6/issue` | 403 `missing_auth` |
| `POST /api/ggv/finance/pack6/xero` | 403 `missing_auth` |
| `GET /api/health` `:8788` | 200 `root` beta-os |
| `GET /api/health` `:8787` | 200 port 8787 |

The route sits behind the existing GGV finance identity wall. The page was not clicked. The unit test calls `dispatch` directly: Amanda `GET /api/ggv/finance/pack6` returns the live snapshot (`live_notas` 0, seed labeled, not allocated); `POST /pack6/capture` returns `live_capture_refused` 405; `POST /pack6/issue` returns `issue_blocked` 405; `POST /pack6/xero` returns `xero_write_blocked` 405.

## Tests

`scripts/tests/test_ggv_nota_pack6.py`: 40 passed, 0 failed.

`WOLF_TEST_MODE=1` was set by the test process. `BETA_AUTH_MODE` was not set.

## Left undone

A live nota row. An issued NNNA number. A books line. A supplier merge. Xero. Phone commission (Matt and Amanda). `staff_ready`.

## NEXT — Pack 7, not started

Guest stay. Reservations are not “one row means no guests”; use an authoritative PMS or say UNAVAILABLE, then pre-arrival and post-stay. Housekeeping is later. Pack 8 recipe variance was not started. This pack did not open guest stay.
