# OPSFIX-3 result

29 Sep 2026. Beta only, branch `build/wolf-command-rebuild`. Operate Wolf: honest Owner Command, data-quality exception register, four human test cards, three small staff defects. Production `:8787` pid **15975** was not restarted. Atrium sidecar `:8790` pid **96416** was not restarted (IDR source fixed in `~/atrium-finance`; Command Centre already used IDR). Nobody was marked `staff_ready` or `human_commissioned`. No write to ESB, Alchemist, Gmail, Xero, Metricool, or banks. No push.

Beta listener pid **46154** started Tue Sep 29 2026, parent pid 1, from `/Users/wolfterminal/beta-os/scripts/serve_beta.py` with `BETA_AUTH_MODE` unset. Previous Beta pid 24551 was stopped. Unsigned `GET /api/health` is 200. Unsigned `GET /wolf` is 403.

Decision served: Matt 29 Sep 2026 07:13 — OPERATE WOLF, DON'T JUST POLISH IT (extends OPSFIX-1/2 on `build/wolf-command-rebuild`).

## Items

1. **FIXED.** Owner Command "What is going wrong?", "Who or what is blocked?", and "Where is money at risk?" roll up material unresolved exceptions from real state: Uma Daily Close BLOCKED, data-quality exceptions, finance books UNAVAILABLE, month-end bank-statement gate, human commissioning FAILs, and failed/degraded integrations when present. Count plus top items in plain English with links. It no longer says "Nothing is going wrong…" while these are open. Live answer: "10 material exceptions are open. Top: Uma Blu Daily Close is BLOCKED; Cash tile — owed to you; Atrium occupancy." Shot `docs/wolf/ops/shots/opsfix3-owner-wolf.png`.

2. **FIXED.** Data-quality exception register at `state/ops/data-quality-exceptions.json`, owner API `GET /api/owner/data-quality`, page `/owner/data-quality`, linked from Owner Command and the War Room. Status OPEN, owner role, "Do not act on this number" on every item. No number was corrected.

### Trace results (plain words)

**a. Cash tile "owed to you" Rp 128,532,978,747**  
What it is: remaining balance on the Atrium apartment sales orderbook (contract − collected), not day-to-day trade AR.  
Where it comes from: wolf-system `money-brain.py` `owed_to_you()` summing sheet BALANCE_ROW; snapshot `owed_total_blended` / `sales_pipeline_outstanding_total`.  
What is wrong: mislabelled as money owed to you / receivables. Xero AR in the same snapshot is 0.  
What would settle it: a commissioned GGV AR figure kept separate from the apartment sales pipeline.

**b. Atrium occupancy 1.75%**  
What it is: Cloudbeds `percentageOccupied` for today.  
Where it comes from: `command-brief` → master atrium tile; live check 2 rooms occupied ÷ 114 capacity ≈ 1.75%.  
What is wrong: live dashboard snapshot, not a night-audit; docs still say 120 rooms while capacity is 114.  
What would settle it: authorised night-audit rooms sold ÷ rooms available for a named business date.

**c. Alchemist payable Rp 62,950,910 · broken 55**  
What it is: unpaid ledger SUM ≈ Rp 62,950,910; broken = Received PR still linked to a paid ledger (55 rows).  
Where it comes from: `alchemist_tile.compute_five()` on `~/.openclaw/workspace/alchemist/data/alchemist.db`.  
What is wrong: desync between PR status and ledger payment; nota files for these 55 are not on local disk.  
What would settle it: PO + receiving + nota on disk + consistent ledger per PR. Bank lines prove bank transactions only and do not establish AP. No "bank beats Alchemist" copy exists in Beta (none found to remove).

**55-record classification:** ESTABLISHED **0** · PARTIAL **55** · NO EVIDENCE **0**. Full list on the register under `dq-alchemist-broken-payable`.

3. **FIXED.** Four plain-language human test cards on the War Room GIVE THIS TO A HUMAN NOW queue and in `state/ops/testability-matrix.json` (Devi, Amanda, Zayen, Haikal), each with who, Beta URLs, 5–8 steps, PASS looks like, and feedback via existing MY COMMISSIONING (`/progress#commissioning`). Earlier FAIL text kept. `staff_ready` and `human_commissioned` stay false. Shot `opsfix3-war-room-human-queue.png`.

4. **FIXED.** My Work Habitat cards use plain footnotes ("From the Habitat plan, 14 Sep. Not yet checked in Wolf."). Duplicate Working_Draft fortnight rows collapse to one; Human_Approved stays separate. Uma Today and Amanda invoice cards drop engineering tags; invoice paths hidden, Open file kept. Shots `opsfix3-haikal-mywork.png`, `opsfix3-uma-today.png`, `opsfix3-amanda-invoices.png`.

5. **FIXED.** Amanda on GGV Finance shows `ROLE-GGV-FINANCE-OPERATOR` from the active path context, not primary Content. Authority unchanged. Same Amanda shot.

6. **FIXED.** Atrium Finance IDR: shared `formatMoneyIDR` / `formatIDR` in `~/atrium-finance/src/utils/idrFormat.ts` wired into General Ledger, Trial Balance, Journal Workbench, and Manual Journal (Rp, thousand separators, no decimals; `$` column headers → Rp). Command Centre already used IDR. Sidecar process not restarted. Shot `opsfix3-atrium-finance-idr.png`.

## Tests this session

| File | Result |
| --- | --- |
| `scripts/tests/test_opsfix3_20260929.py` | SUMMARY pass=88 fail=0, RESULT: PASS |
| `scripts/tests/test_opsfix2_20260928.py` | SUMMARY pass=45 fail=0, RESULT: PASS |
| `scripts/tests/test_opsfix1_20260928.py` | SUMMARY pass=42 fail=0, RESULT: PASS |
| `scripts/tests/test_staff_access_20260928.py` | SUMMARY pass=274 fail=0 |
| `scripts/tests/test_role_routing_20260928.py` | SUMMARY pass=84 fail=0 |
| `scripts/tests/test_atrium_full_mount_20260928.py` | SUMMARY pass=79 fail=0 |
| `scripts/tests/test_umareal_20260928.py` | SUMMARY pass=85 fail=0 |
| `scripts/tests/test_opsaudit_20260928.py` | SUMMARY pass=109 fail=0, RESULT: PASS |

## Pids

| Process | Pid |
| --- | --- |
| Production `:8787` | 15975 (unchanged) |
| Atrium sidecar `:8790` | 96416 (unchanged) |
| Beta `:8788` | 46154 (replaced 24551) |

## Commits

Local only. No push.

RESULT: PASS
