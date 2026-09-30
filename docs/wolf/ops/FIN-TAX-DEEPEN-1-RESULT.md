# FIN-TAX-DEEPEN-1 RESULT — Tax dues deepen (wire or HUMAN/EXTERNAL)

**As of:** 2026-09-30 ~08:49 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start CRM-PIPELINE-TRUTH-1 / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 Wave8 pack FIN-TAX-DEEPEN-1** (armed after INV-CASH-FACTS-ROUTE-1 PASS_VERIFIED).  
Challenges **FIN-TAX-SHELL-1 UNKNOWN dues ceiling**.  
**Probe authorised tax systems; wire facts OR stamp HUMAN_COMMISSIONING/EXTERNAL_BLOCKER with evidence — never invent dues, filings, or NPWP.**  
**Google NPWP = MATT_ACTION Owner-only non-blocking.**  
Preserves **FIN-TAX-SHELL-1**.  
**Not PROVEN/READY.**

## Probe / route findings

| Probe | Result | Evidence |
| --- | --- | --- |
| Tax systems (name-only) | **ABSENT** | No TAX_/DJP_/EFAKTUR/SPT_/PPN_/PPH_ keys; no authorised tax client |
| DJP / eFaktur / e-filing | **EXTERNAL_BLOCKER** | No `djp_client` / `efaktur_client` in-repo; live path not authorised |
| FIN-TAX-SHELL-1 facts | **UNKNOWN** · filing_count=0 | Calendars/obligations null dues · preserved |
| Google NPWP | **MATT_ACTION** non-blocking | Owner-only; pack does not wait on NPWP |
| Human route commission stamp | **ABSENT** | No `FIN-TAX-DEEPEN-1-COMMISSION.json` |
| Route decision | **STAMP_HUMAN_COMMISSIONING** | Systems absent → refuse invent dues |
| due_amount / due_on / npwp_number | **null** | Never invented |

## Commissioning path (documented)

1. **Owner authorises tax fact systems** in the authorised secret store + connector (DJP Online / eFaktur / internal tax ledger — not invented by agents).
2. **Owner writes commission stamp** `state/final-completion/packs/FIN-TAX-DEEPEN-1-COMMISSION.json` with `human_route_commissioned=true` (or `tax_facts_authorised=true`).
3. **Parent arms wire pack** after stamp + verified authorised systems with real dues/filings. This pack EXIT never invents dues, filings, or NPWP.
4. **Until then: UNKNOWN shell preserved** — FIN-TAX-SHELL-1 filing_count=0; DJP/eFaktur EXTERNAL_BLOCKER; NPWP MATT_ACTION non-blocking.

## What landed

### 1) Tax dues deepen board
- Page `/fin/tax-deepen-1` (`dashboards/fin-tax-deepen-1.html`)
- Pack classification pin **INTERNALLY_SOLVABLE_OR_HUMAN**
- Route classification **HUMAN_COMMISSIONING** · DJP/eFaktur **EXTERNAL_BLOCKER** · NPWP **MATT_ACTION**
- Surfaces: tax systems · DJP EXTERNAL_BLOCKER · NPWP MATT_ACTION · tax shell facts · human route · route decision · FIN-TAX-SHELL preserved · invent refused
- `invented_amount=false` · `invented_filing=false` · `invented_npwp=false` · `due_amount=null`

### 2) Auth page + API
- API `GET /api/fin/tax-deepen-1` (aliases `/api/ops/fin-tax-deepen-1` · `/api/ops/tax-deepen-1`)
- Unsigned → **403** · Amanda → Access denied · Matt → HUMAN_COMMISSIONING board
- POST due_amount / filing / npwp / staff_ready / human_commissioned → **403**

### 3) Honesty pins
| Pin | Value |
| --- | --- |
| Pack classification | **INTERNALLY_SOLVABLE_OR_HUMAN** |
| Route classification | **HUMAN_COMMISSIONING** |
| Action | **STAMP_HUMAN_COMMISSIONING** |
| DJP / eFaktur | **EXTERNAL_BLOCKER** |
| NPWP | **MATT_ACTION** (non-blocking) |
| Dues / filing invent | **false / refused** |
| FIN-TAX-SHELL-1 | **PRESERVED** — filing_count=0 UNKNOWN · no fake filings |
| `staff_ready` / `human_commissioned` | **false** |
| Next pack | **CRM-PIPELINE-TRUTH-1** (parent/Peaches only — Cursor did not auto-chain during pack; Matt auto-continue arms after Peaches) |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_fin_tax_deepen1_20260930.py` | **PASS=179 FAIL=0** |

Shots under `docs/wolf/ops/shots/`: `fintaxdeepen1-desk-desktop.png`, `fintaxdeepen1-desk-phone.png`, `fintaxdeepen1-route-stamps.png`, `fintaxdeepen1-unsigned-deny.png`.

## Files

- Core: `scripts/core/fin_tax_deepen1.py`
- Serve: `scripts/serve_beta.py` (`_fin_tax_deepen1_dispatch` / write refuse)
- UI: `dashboards/fin-tax-deepen-1.html`
- Shell crumbs/canonical: `scripts/core/wolf_shell.py`
- Tests: `scripts/tests/test_fin_tax_deepen1_20260930.py`
- Stamp: `state/final-completion/packs/FIN-TAX-DEEPEN-1-ARM.json`

## Out of scope (not started from this EXIT)

- **CRM-PIPELINE-TRUTH-1** (next — Peaches/parent arms after verify; pack suite did not auto-chain during build)
- Inventing dues, filings, or NPWP numbers
- Wiring live DJP / eFaktur without Owner commission
- Flipping `staff_ready` / `human_commissioned` via API
- HEADCHEF / Exit Report / prod mutate / push
- Claiming CAP-FIN tax PROVEN/READY

## Classification

Ceiling **FIN-TAX-SHELL-1 UNKNOWN dues** → disposition **HUMAN_COMMISSIONING** (pack umbrella INTERNALLY_SOLVABLE_OR_HUMAN) until Owner authorises tax systems and commissions the route.  
Live DJP/eFaktur stamped **EXTERNAL_BLOCKER**.  
Google NPWP remains **MATT_ACTION** non-blocking.  
FIN-TAX-SHELL-1 preserved. Never invent dues/filings/NPWP.

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · classification HUMAN_COMMISSIONING · pack INTERNALLY_SOLVABLE_OR_HUMAN · DJP EXTERNAL_BLOCKER · NPWP MATT_ACTION non-blocking · FIN-TAX-SHELL-1 preserved · no push · did not auto-chain next pack during build.
