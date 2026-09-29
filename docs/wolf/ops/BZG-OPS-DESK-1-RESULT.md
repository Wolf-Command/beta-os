# BZG-OPS-DESK-1 RESULT — BZG ops desk unify (outlets + venue-pnl + foundations)

**As of:** 2026-09-30 ~01:27 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta `:8788` restarted (launchd)  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start FIN-RECON-SHELL-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **2026-09-20 PICK CAP-BZG-02** venue P&L & management rollup skeleton, deepened by **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack BZG-OPS-DESK-1** (armed after INTEL-LEARN-1 PASS_VERIFIED).  
Unifies prior packs without inventing sales/P&L. **Not PROVEN / READY.**

## Facts available vs UNKNOWN (honest)

| Source | Status |
| --- | --- |
| `org_outlet_registry` (7 outlets) | **FACT** — Uma OPEN · Rainforest + Pool Bar PRE-OPENING |
| `venue_daily_closes` | **0 rows** → revenue/cost/contribution = **UNKNOWN** (not zero) |
| Venue P&L master | **`insufficient_facts`** |
| Cross-outlet foundations | Hooks usable · centres null · empty OK |
| Invented sales / multi-outlet totals | **false** |

## What landed

### 1) Single Beta ops desk
- Core `scripts/core/bzg_ops_desk1.py` composes outlet registry + venue-pnl rollup + xoutlet foundations
- Preserves `/bzg/outlets`, `/bzg/venue-pnl`, FC-SHELL-2 — does not replace them
- Wolf shell BZG **Operations** grammar → `/bzg/ops-desk` (live)

### 2) Auth page + API
- Page: `/bzg/ops-desk` (alias `/bzg/ops`)
- API: `GET /api/bzg/ops-desk`
- Unsigned → **403** · Amanda → Access denied · Zayen/Matt → desk with UNKNOWN money slots
- POST fake sales / ready / payment → **403**
- Finance-only wall allowlists ops-desk paths (Zayen)

### 3) Honesty
| Pin | Value |
| --- | --- |
| CAP-BZG-02 | **SPECIFIED** · ceiling BUILT · `cap_bzg_02_proven=false` |
| `venue_daily_closes` | **0** → UNKNOWN |
| Invented sales / P&L | **false** |
| `staff_ready` / `human_commissioned` | **false** |
| Live P&L / READY / PROVEN | **false** |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_bzg_ops_desk1_20260930.py` | **PASS=114 FAIL=0** |
| `scripts/tests/test_bzg_venuepl1_20260929.py` (re-run) | **PASS=86 FAIL=0** |

## Shots (8/8)

Under `docs/wolf/ops/shots/`:
- `bzgopsdesk1-desk-{desktop,phone}.png` — unified desk (outlets + foundations)
- `bzgopsdesk1-unknown-{desktop,phone}.png` — UNKNOWN / insufficient_facts
- `bzgopsdesk1-amanda-deny-{desktop,phone}.png` — Amanda Access denied
- `bzgopsdesk1-unsigned-deny-{desktop,phone}.png` — unsigned Access denied

## Files

- Core: `scripts/core/bzg_ops_desk1.py` · `staff_access.py` · `wolf_shell.py`
- UI: `dashboards/bzg-ops-desk.html`
- Serve: `scripts/serve_beta.py` (`_bzg_ops_desk1_dispatch` + write refuse)
- Tests: `scripts/tests/test_bzg_ops_desk1_20260930.py`
- Shots: `scripts/audit/bzgopsdesk1_shots.py`
- Stamp: `state/final-completion/packs/BZG-OPS-DESK-1-ARM.json`

## Out of scope (not started from this EXIT)

- **FIN-RECON-SHELL-1** (next queue — Peaches/parent arms after verify; Cursor must not auto-chain)
- Fake sales, HEADCHEF / Exit Report
- Claiming CAP-BZG-02 PROVEN/READY
- Prod mutate, push, flipping commissioning flags

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.
