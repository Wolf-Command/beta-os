# INV-CASH-FACTS-ROUTE-1 RESULT — Inventory/cash facts route (wire or human)

**As of:** 2026-09-30 ~08:55 WITA · **Branch:** `build/wolf-command-rebuild` (beta-os)  
**Ports:** Prod `:8787` pid **15975** READ-ONLY untouched · Beta test harness ephemeral  
**Flags:** `staff_ready=false` · `human_commissioned=false` · **No push** · **Did not start DEEPEN-SYNTH-CONTINUE / HEADCHEF / Exit Report**

## Decision / canon

Serves **FINAL_WOLF_COMPLETION_MISSION Phase 2 pack INV-CASH-FACTS-ROUTE-1** (armed after FIN-BANK-CREDS-ROUTE-1 PASS_VERIFIED).  
Challenges **UNKNOWN inventory/cash shells**.  
**Probe authorised count/cash systems; wire facts OR stamp HUMAN_COMMISSIONING/EXTERNAL with evidence — never invent qty or cash.**  
Preserves **BZG-INVENTORY-TRUTH-1** + **FIN-CASH-TRUTH-1**.  
**Not PROVEN/READY.**

## Probe / route findings

| Probe | Result | Evidence |
| --- | --- | --- |
| Inventory / count systems (name-only) | **ABSENT** | No INVENTORY_/COUNT_/STOCK_/POS invent keys; no authorised count client |
| Cash facts systems (name-only) | **ABSENT** | No PETTY_CASH_/CASH_DRAWER_/CASH_FACTS_ keys; no empire cash-facts client |
| Uma Alchemist petty_cash | **EXTERNAL** | Entity-scoped RO — not wired into FIN-CASH-TRUTH-1 / BZG-INVENTORY-TRUTH-1 |
| BZG-INVENTORY-TRUTH-1 facts | **UNKNOWN** · fact_count=0 | No qty to wire |
| FIN-CASH-TRUTH-1 facts | **UNKNOWN** · import_count=0 | FILE_IMPORT_ONLY · balances null |
| Human route commission stamp | **ABSENT** | No `INV-CASH-FACTS-ROUTE-1-COMMISSION.json` |
| Route decision | **STAMP_HUMAN_COMMISSIONING** | Systems absent → refuse invent qty/cash |
| qty / balance / cash_on_hand | **null** | Never invented |

## Commissioning path (documented)

1. **Owner authorises count / cash fact systems** in the authorised secret store + connector (not invented by agents).
2. **Owner writes commission stamp** `state/final-completion/packs/INV-CASH-FACTS-ROUTE-1-COMMISSION.json` with `human_route_commissioned=true` (or `inv_cash_facts_authorised=true`).
3. **Parent arms wire pack** after stamp + verified authorised systems with real facts. This pack EXIT never invents qty or cash.
4. **Until then: UNKNOWN shells preserved** — BZG-INVENTORY fact_count=0; FIN-CASH FILE_IMPORT_ONLY / balances null.

## What landed

### 1) Facts route board
- Page `/ops/inv-cash-facts-route-1` (`dashboards/inv-cash-facts-route-1.html`)
- Pack classification pin **HUMAN_COMMISSIONING_OR_INTERNAL**
- Route classification **HUMAN_COMMISSIONING** · Uma surface **EXTERNAL**
- Surfaces: count systems · cash systems · Uma EXTERNAL · inv facts · cash facts · human route · route decision · BZG-INV preserved · FIN-CASH preserved · invent refused
- `invented_qty=false` · `invented_cash=false` · `qty=null` · `balance=null`

### 2) Auth page + API
- API `GET /api/ops/inv-cash-facts-route-1` (aliases `/api/fin/…` · `/api/bzg/…`)
- Unsigned → **403** · Amanda → Access denied · Matt → HUMAN_COMMISSIONING board
- POST qty / cash / invent-balance / fake-stock / staff_ready / human_commissioned → **403**

### 3) Honesty pins
| Pin | Value |
| --- | --- |
| Pack classification | **HUMAN_COMMISSIONING_OR_INTERNAL** |
| Route classification | **HUMAN_COMMISSIONING** |
| Action | **STAMP_HUMAN_COMMISSIONING** |
| Uma petty_cash | **EXTERNAL** (not wired into empire shells) |
| Qty / cash invent | **false / refused** |
| BZG-INVENTORY-TRUTH-1 | **PRESERVED** — fact_count=0 UNKNOWN · no fake stock |
| FIN-CASH-TRUTH-1 | **PRESERVED** — FILE_IMPORT_ONLY · no invented balances |
| `staff_ready` / `human_commissioned` | **false** |
| Next pack | **DEEPEN-SYNTH-CONTINUE** (parent/Peaches only — Cursor did not auto-chain) |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_inv_cash_facts_route1_20260930.py` | **PASS=172 FAIL=0** |

Shots under `docs/wolf/ops/shots/`: `invcashfacts1-desk-desktop.png`, `invcashfacts1-desk-phone.png`, `invcashfacts1-route-stamps.png`, `invcashfacts1-unsigned-deny.png`.

## Files

- Core: `scripts/core/inv_cash_facts_route1.py`
- Serve: `scripts/serve_beta.py` (`_inv_cash_facts_route1_dispatch` / write refuse)
- UI: `dashboards/inv-cash-facts-route-1.html`
- Shell crumbs/canonical: `scripts/core/wolf_shell.py`
- Tests: `scripts/tests/test_inv_cash_facts_route1_20260930.py`
- Stamp: `state/final-completion/packs/INV-CASH-FACTS-ROUTE-1-ARM.json`

## Out of scope (not started from this EXIT)

- **DEEPEN-SYNTH-CONTINUE** (next — Peaches/parent arms after verify; Cursor must not auto-chain)
- Inventing qty, cash, balances, or fake stock
- Wiring Uma Alchemist petty_cash into FIN-CASH-TRUTH-1
- Flipping `staff_ready` / `human_commissioned` via API
- HEADCHEF / Exit Report / prod mutate / push
- Claiming CAP-BZG inventory / CAP-FIN cash PROVEN/READY

## Classification

Ceiling **Inventory/cash UNKNOWN shells** → disposition **HUMAN_COMMISSIONING** (pack umbrella HUMAN_COMMISSIONING_OR_INTERNAL) until Owner authorises count/cash systems and commissions the route.  
Uma Alchemist petty_cash stamped **EXTERNAL** (entity-scoped, not empire cash truth).  
BZG-INVENTORY-TRUTH-1 + FIN-CASH-TRUTH-1 preserved. Never invent qty/cash.

## EXIT

**EXIT:0**

`staff_ready=false` · `human_commissioned=false` · prod pid 15975 untouched · classification HUMAN_COMMISSIONING · pack HUMAN_COMMISSIONING_OR_INTERNAL · Uma EXTERNAL · BZG-INVENTORY-TRUTH-1 + FIN-CASH-TRUTH-1 preserved · no push · did not auto-chain next pack.
