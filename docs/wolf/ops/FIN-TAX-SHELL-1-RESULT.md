# FIN-TAX-SHELL-1 RESULT — Tax calendar shell honesty (no fake filings)

**As of:** 2026-09-30 ~04:01 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os @ `902c9d8`)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start BZG-INVENTORY-TRUTH-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack FIN-TAX-SHELL-1** (armed after SOP-LESSON-LIVE-1 PASS_VERIFIED).  
Tax calendar stubs stay **UNKNOWN** until facts — never invent due amounts or fake filings.  
Preserves **FC-SHELL-2**. Honest close-toward: **CAP-FIN tax** (ceiling **BUILT**; not PROVEN/READY).

## What landed

### 1) Tax calendar shell (honest empty)
| Surface | Status |
| --- | --- |
| Entity calendars (BZG / GGV / AMG) | **UNKNOWN** · due_amount=null · due_on=null · filed=false |
| Obligation slots (PPN / PPh 21 / PPh 23 / SPT Tahunan Badan) | **UNKNOWN** · due_amount=null · filed=false |
| filing_count | **0** |
| Fake filings / invented dues | **false** |

### 2) Auth page + API
- Page `/fin/tax-shell-1` (`dashboards/fin-tax-shell-1.html`; aliases `/fin/tax-shell`, `/fin-tax-shell-1`)
- API `GET /api/fin/tax-shell-1` (auth) → slice payload
- Unsigned → **403** (fail-closed)
- POST invent-filing / invent-amount / due → **403** (`invent_filing_refused` / `invent_amount_refused`)

### 3) Preserved packs (read-only)
| Pack | Status |
| --- | --- |
| FC-SHELL-2 | **PRESERVED** — BZG/GGV 200/0 · AMG live untouched |

### 4) Honesty pins
| Pin | Value |
| --- | --- |
| CAP-FIN tax | **SPECIFIED** · ceiling BUILT · not PROVEN/READY |
| `due_amount` / `due_on` | **null** |
| Live filing / invented filing / fake tax amounts | **false** |
| `staff_ready` / `human_commissioned` | **false** |
| Next pack | **BZG-INVENTORY-TRUTH-1** (parent/Peaches only — Cursor did not auto-chain) |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_fin_tax_shell1_20260930.py` | **PASS=161 FAIL=0** |

Shots: `docs/wolf/ops/shots/fintaxshell1-desk-desktop.png`, `fintaxshell1-desk-phone.png`, `fintaxshell1-calendar-unknown.png`, `fintaxshell1-fc-shell2-preserved.png`, `fintaxshell1-unsigned-deny.png`.

## Files

- Core: `scripts/core/fin_tax_shell1.py`
- Serve: `scripts/serve_beta.py` (`_fin_tax_shell1_dispatch` + write refuse)
- UI: `dashboards/fin-tax-shell-1.html`
- Shell crumbs/canonical: `scripts/core/wolf_shell.py`
- Tests: `scripts/tests/test_fin_tax_shell1_20260930.py`
- Stamp: `state/final-completion/packs/FIN-TAX-SHELL-1-ARM.json`

## Out of scope (not started from this EXIT)

- **BZG-INVENTORY-TRUTH-1** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Fake filings, invented tax due amounts
- HEADCHEF / Exit Report / prod mutate / push / flipping commissioning flags

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · no push · did not auto-chain next pack.
