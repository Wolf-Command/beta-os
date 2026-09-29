# BZG-VENUEPL-1 RESULT — Venue P&L rollup skeleton (facts only)

**As of:** 2026-09-30 ~00:05 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os) · atrium-finance `wolf/beta-mount-20260928` @ `7584266` (untouched this pack)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` restarted (launchd) · Sidecar `:8790` was down; restart attempt failed on session mount (pre-existing — this pack did not change atrium)  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start SOP-FACTORY-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION** Phase 2 pack BZG-VENUEPL-1 (after FC-SHELL-2 PASS_VERIFIED).  
Closes toward CAP-BZG-02 / IL-R5 venue-as-mini-business — **not** PROVEN / READY.

## Facts available vs UNKNOWN (honest)

| Source | Status |
| --- | --- |
| `org_outlet_registry` (7 outlets) | **FACT** — identity + status on every card |
| `venue_daily_closes` | **0 rows** → revenue/cost from closes = **UNKNOWN** |
| BZG books `journal_lines` (`atrium-bzg.sqlite`) | COA template 200 accounts / **0 journals** → books P&L = **UNKNOWN** |
| ESB warehouse (`esb.sqlite`, branch BLZ/Uma) | **READ_OK**, ~177 distinct biz_dates present as warehouse facts — **not** placed into revenue/contribution slots until bound by a `venue_daily_close` |
| Master BZG aggregate | **`insufficient_facts`** — no invented progress toward any contribution target |

Uma stays **OPEN**. Rainforest + Pool Bar stay **PRE-OPENING**. Future outlets PRE-OPENING.

## What landed

### 1) Per-outlet read-only rollup
- `scripts/core/bzg_venue_pnl.py` — `outlet_card` / `build_outlet_rollup` compose registry + close/journal/ESB probes
- Slots: venue/status = FACT from registry; revenue/cost/contribution/rollup = **UNKNOWN** when no close/journal facts (not zero-as-success)
- Empty CAP-BZG-02 framework (`/api/bzg/venue-pnl/framework`) preserved

### 2) Beta surfaces
- `/bzg/venue-pnl` + `/api/bzg/venue-pnl/rollup` + `/api/bzg/venue-pnl/outlets/{id}`
- `/bzg/outlets` overview gains `venue_pnl_rollup` teaser panel
- Wolf shell BZG grammar: Venue P&L live link
- Authority: Zayen BZG board allow (finance-only wall allowlisted for venue-pnl) · Matt progress.read · Amanda **403** · Hari **403** · Ext Acct unseated
- Writes (payment/bank/books/ready/proven/…) still refused

### 3) Honesty
- No fake sales/P&L/budgets/allocations/go-live numbers
- No READY / staff_ready / human_commissioned banners or flag flips
- CAP-BZG-02 stays SPECIFIED; ceiling BUILT; CR open

## Tests

| Suite | Result |
| --- | --- |
| `test_bzg_venuepl1_20260929.py` | **PASS=86 FAIL=0** |
| `test_bzg_outlet1_20260929.py` | **PASS=82 FAIL=0** |
| `test_bzg_xoutlet1_20260929.py` | **PASS=90 FAIL=0** |
| `test_fc_shell2_20260929.py` | **pass=72 fail=0** |

## Shots (8/8)

Under `docs/wolf/ops/shots/`:
- `bzgvenuepl1-master-{desktop,phone}.png` — master insufficient_facts
- `bzgvenuepl1-uma-open-{desktop,phone}.png` — Uma OPEN (honest EMPTY/UNKNOWN money slots)
- `bzgvenuepl1-rain-preopening-{desktop,phone}.png` — Rainforest PRE-OPENING
- `bzgvenuepl1-amanda-deny-{desktop,phone}.png` — Amanda 403

## Files

- Core: `scripts/core/bzg_venue_pnl.py` · `scripts/core/staff_access.py` (finance-only allowlist) · `scripts/core/bzg_outlet_registry.py` · `scripts/core/wolf_shell.py`
- UI: `dashboards/bzg-venue-pnl.html` · `dashboards/bzg-outlets.html`
- Serve: `scripts/serve_beta.py`
- Tests: `scripts/tests/test_bzg_venuepl1_20260929.py`
- Shots: `scripts/audit/bzgvenuepl1_shots.py`
- Stamp: `state/final-completion/packs/BZG-VENUEPL-1-ARM.json`

## Out of scope (not started from this EXIT)

- **SOP-FACTORY-1** (next queue — Peaches/parent arms after verify; Cursor must not auto-chain)
- HEADCHEF / Exit Report / claiming CAP-BZG-02 PROVEN/READY
- Fake closes, ESB totals invented into P&L slots, seating Ext Acct, prod mutate, push

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.
