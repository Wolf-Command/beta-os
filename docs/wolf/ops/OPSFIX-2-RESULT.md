# OPSFIX-2 result

28 Sep 2026. Beta only, branch `build/wolf-command-rebuild`. Extends My Work, Owner Command, Uma Blu Today and Bills, and the GGV invoice list. Production `:8787` pid 15975 was not restarted. Atrium sidecar `:8790` pid 96416 was not restarted. Nobody was marked `staff_ready` or `human_commissioned`. No write to ESB, Alchemist, Gmail, Xero, or Metricool. No new ESB API call. No push.

Beta listener pid **24551** started Mon Sep 28 23:39:48 2026, parent pid 1, from `/Users/wolfterminal/beta-os/scripts/serve_beta.py` with `BETA_AUTH_MODE` unset. Previous Beta pid 21260 was stopped. Unsigned `GET /api/health` is 200. Unsigned `GET /wolf` and `GET /bzg/uma-blu` are 403.

## Items

1. **FIXED.** My Work pins the truth card to `#1c1915` on `#fffdf8` and the work cards to `#1c1408` on `#f4e4c4`, with the provenance footnote at `#3f3422` on the same gold. Those pairs pass WCAG AA for normal text. The colours are literal hex with `!important`, so the shell token sheet cannot wash them back to pale teal. Shot `docs/wolf/ops/shots/opsfix2-haikal-mywork.png` (1024).

2. **FIXED.** Staff projection of Habitat plans omits `data_lane=test`. Plans 1–3 stay in `content_plans` (9 stored). Haikal's home returns the six operational plans, source ids 4–9, with no `data_lane` field on the row. Creators still receive plans by experience and brand scope, not by person id. `core_work_items` stays 0.

3. **FIXED.** Each work card leads with the plan title, the date range, the status in staff words, and "Open plan" as the link. Provenance (`origin=historical`, `verified_by_wolf=false`, source id) is the footnote under that line. Same shot as item 1.

4. **FIXED.** Owner Command "What changed?" reads: "On 28 Sep 2026, GGV: the next invoice number was set. 8 recent changes are on record for these companies." The event code is not on the card. "What is going wrong?" reads: "Nothing is going wrong on the operating record." The stored practice rows are not mentioned, because the valid operational exception count is 0. Shot `docs/wolf/ops/shots/opsfix2-owner-wolf.png` (1024).

5. **FIXED.** Uma Blu Today reads finished BLZ bills from the local ESB warehouse. Latest business day 27 Sep 2026: 61 bills, 94 covers, Rp 19,252,190. The seven days ending that day are on the page (21 Sep Rp 18,225,000 through 27 Sep Rp 19,252,190). Today in this session is 28 Sep 2026 WITA, so 27 Sep is yesterday and the STALE banner stays off. The rule is: show the banner with the last day present only when that day is older than yesterday. Shots `opsfix2-uma-today-desktop.png` (1024) and `opsfix2-uma-today-phone.png` (390).

6. **FIXED.** Bills lists the Alchemist `pr_orders` book, 504 rows, labelled historical and read-only. Example catalog rows stay out. A nota links only when a local jpg name contains the photo basename or Drive id. This read matched 0 of 504. 409 rows have no photo URL. The other 95 are Drive links whose ids are not in `~/.openclaw/workspace/alchemist/notas`. Every row therefore says EVIDENCE FILE NOT RECOVERABLE. No photo was invented. Shot `opsfix2-uma-bills.png` (1024).

7. **FIXED.** Today has an EXCEPTIONS block from the live reads. 19 dishes have a missing cost, linked to `/bzg/uma-blu/recipes`. Sold on 27 Sep with no recipe, top by quantity: Cappucino Hot 15, Big Blu Carnivora 14, Cappucino iced 12, Bonsoy Substitute 11, Caffee Lattee Iced 10, Fresh coconut 8, Cookies 8, Extra Sourdough 7. 99 prices are stale. Bake House is stored 2 times (suppliers 5 and 90). Daily close is BLOCKED: variance policy count 0, closer count 0, `branch_blocked` true, `page_blocked` false. The Daily Close nav still opens `/uma-blu-close` and is labelled "Daily Close · BLOCKED". The Today page stays open. A closer was not seated.

8. **FIXED.** Today, Bills, and the recipe, purchasing, and sales pages format IDR as `Rp` with thousand separators and no decimals. The 27 Sep net is `Rp 19,252,190`. Recipe costs use the same formatter.

9. **FIXED.** Real local files were found. Search record, also returned on Amanda's invoice list: Beta catalog `ggv_invoices` holds 0 of these numbers; three Xero mirror copies of `sales_invoice` stop at 061A; `~/.openclaw/workspace/wolf-system/state/pdfs` has 40 branded PDFs from 021A through 066A; Gmail export files on disk: none found. Gaps between 021A and 066A were not filled in. Projected read-only, `inserted=false`, `origin=historical`, `verified_by_wolf=false`:

| Number | Date | Customer | Total | File |
| --- | --- | --- | --- | --- |
| 064A | 14 Sep 2026 | Habitat Vibe Developments | Rp 175,000,000 | `2026-09-14-GGV-064A-branded.pdf` |
| 065A | 21 Sep 2026 | PT The One Partners | Rp 30,000,000 | `2026-09-21-GGV-065A-branded.pdf` |
| 066A | 28 Sep 2026 | PT Keen Eye | Rp 263,050,160 | `2026-09-28-GGV-066A-branded.pdf` |

`fin_invoice_sequences` for ENT-GGV stays `next_value` 67 (`{n:03d}A`). Amanda can open the 066A file; the bytes start as a PDF. Devi is 403. Shot `opsfix2-amanda-invoices.png` (1024). Bank lines and guest line items from the PDFs are not on the desk.

## Tests this session

| File | Result |
| --- | --- |
| `scripts/tests/test_opsfix2_20260928.py` | SUMMARY pass=43 fail=0, RESULT: PASS |
| `scripts/tests/test_opsfix1_20260928.py` | SUMMARY pass=42 fail=0, RESULT: PASS |
| `scripts/tests/test_staff_access_20260928.py` | SUMMARY pass=274 fail=0 |
| `scripts/tests/test_role_routing_20260928.py` | SUMMARY pass=84 fail=0 |
| `scripts/tests/test_atrium_full_mount_20260928.py` | SUMMARY pass=79 fail=0 |
| `scripts/tests/test_umareal_20260928.py` | SUMMARY pass=85 fail=0 |
| `scripts/tests/test_opsaudit_20260928.py` | SUMMARY pass=97 fail=0, RESULT: PASS |

`state/ops/testability-matrix.json` keeps earlier FAIL text ("Commissioning FAIL on the earlier small desk", "Zayen's FAIL was about the earlier desk"). `staff_ready` and `human_commissioned` stay false. Ready for a human now includes Devi on Uma Blu Today, Uma recipes, and Uma Blu purchasing, and Amanda on GGV invoice history.

## Pids

| Process | Pid |
| --- | --- |
| Production `:8787` | 15975 (unchanged) |
| Atrium sidecar `:8790` | 96416 (unchanged) |
| Beta `:8788` | 24551 (replaced 21260) |

## Commits

Local only. No push.

- Commit hash is recorded in the follow-up line after this file is committed.

RESULT: PASS
