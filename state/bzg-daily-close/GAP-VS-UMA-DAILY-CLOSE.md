# GAP — Authorised closing procedure vs current Uma Blu Daily Close

**Pack:** BZG-DAILY-CLOSE-TILL-EDC-1  
**as_of:** 2026-10-02T19:45:00+08:00 WITA  
**Telegram recovery:** `TELEGRAM_SOURCE_INCOMPLETE` (Desktop chat) · procedure body from Alchemist `/nightly` + canon  
**no_matt_message:** true

## Current foundation (reuse — do not new app)

| Asset | Path | Status |
|---|---|---|
| Canon honesty | `docs/canon/UMA-BLU-DAILY-CLOSE.md` | BUILT 2026-09-17 |
| Engine | `scripts/core/venue_close.py` | Uma-scoped states + SoD |
| ESB snapshot | `scripts/core/esb_close_snapshot.py` | payment lines; settlement **UNAVAILABLE** |
| Migration | `scripts/migrations/021_uma_blu_daily_close.sql` | `venue_daily_closes` + variance policies |
| Tests | `scripts/tests/test_uma_blu_daily_close.py` | present |
| UI | `dashboards/uma-blu-close.html` | present |
| Routes | `/api/venue-close/*`, `/uma-blu-close` | present |
| Declared cash wave | WAVE2-01 | eng proof; physical till still undone |
| Outlet registry | `scripts/core/bzg_outlet_registry.py` | 7 BZG outlets seed |

## Gap matrix

| # | Requirement (Owner / recovered TG bot) | Current Uma Daily Close | Gap | Action |
|---|---|---|---|---|
| G1 | One reusable **BZG Daily Close** engine | Module named/used as Uma Blu close | Engine is venue-generic tables but product surface Uma-only | Generalise config + activate Uma only |
| G2 | Outlet config for **all 7** Owner outlets | Single brand `BZG-UMA` closes | No per-outlet close config / activation flags | Add outlet close config from registry; `human_activate=Uma Blu` only |
| G3 | Till close: POS Z-report **photo evidence** + cash/card/qris/gross | Declared cash + evidence id; ESB totals | No first-class Z-report / tender breakdown object | Add till evidence binding; fields **NEEDS CONFIGURATION** where unknown |
| G4 | **EDC per terminal** settlement slip photo + bank + batch_total | Absent | Critical gap vs TG `/nightly` | Add `close_edc_terminals` / evidence rows; terminal IDs **NEEDS CONFIGURATION** |
| G5 | Card Total = Σ EDC settlements (not ESB card payments alone) | ESB payment-line cash basis only | Must not equate ESB payments to EDC settlement | Keep honesty; add EDC evidence lane separate from ESB |
| G6 | QRIS captured on Z-report | Not on close row | Gap | Capture via till OCR/evidence; do not invent |
| G7 | Bank Part 2 settlement match | `settlement_api: UNAVAILABLE` | Honest | Keep UNAVAILABLE unless proved; Status may show PENDING_BANK / UNAVAILABLE |
| G8 | Variance requires review **without** tolerance | live policy rows=0; non-zero → VARIANCE_REQUIRES_POLICY | Aligns with Owner | **Do not** port Alchemist 2%/Rp5k soft gap as policy |
| G9 | Declared cash ≠ verified cash | HONESTY flag true | OK | Preserve |
| G10 | Exception Work Item + HFB verify SoD | BUILT role/scope | Keep; outlet-scope exceptions | Extend titles/scope to outlet_id |
| G11 | Closer = Assignment/Role/Scope (`ROLE-BZG-CLOSER`) | ROLE built; seat WAITING | Do not hardcode Devi | Wire Assignment; commissioner note only |
| G12 | Mobile-first close | Desktop-oriented `uma-blu-close.html` | Owner UX gap | Mobile-first close surface (reuse pack patterns) |
| G13 | Multi-outlet names | Registry vs Owner titles vs Alchemist OUTLETS diverge | Mapping incomplete | Config map; unknown → NEEDS CONFIGURATION |
| G14 | Till float Rp 1,000,000 (Owner decision 2026-08-02) | Not in venue_close | Deposit-chain concern | Config field from citation; exclude from “takings” math; do not invent other floats |
| G15 | staff_ready / human_commissioned | false | Keep until Devi PASS | Enforce in RESULT |
| G16 | Prod :8787 | Untouched | Keep READ-ONLY | No prod mutate |

## What eng may build without Owner decision

- Reuse/extend `venue_close` + migration for outlet_id + EDC evidence tables with **empty / NEEDS CONFIGURATION** terminal registry  
- Uma-only `human_close_enabled`  
- UI mobile-first for Uma  
- Tests for honesty flags, SoD, no invented tolerance, settlement UNAVAILABLE  
- Exception Work Items outlet-aware  

## STOP_FOR_OWNER (blocks Uma human commission / may block eng proof if forced to invent)

1. Uma Blu **EDC terminal inventory** (count + acquirer labels) — without this, EDC lane must stay config-incomplete (eng may still ship schema + UI with visible NEEDS CONFIGURATION).  
2. Confirm **outlet title map** for Owner’s 7 names vs `org_outlet_registry`.  
3. Confirm soft OCR warn allowed as UX-only (not a tolerance policy).  
4. Variance absolute threshold remains UNRESOLVED — eng must **not** seed ACTIVE policy.

## Variance-tolerance finding

- **Wolf live:** `venue_close_variance_policies` ACTIVE count = **0** (canon + code). Non-zero declared−ESB_CASH_FROM_PAYMENTS → `VARIANCE_REQUIRES_POLICY` → exception.  
- **Alchemist TG bot:** soft POS Gross vs Cash+Card+QRIS warn at max(2%, Rp 5,000) — **not** adopted.  
- **Proposed policy doc:** thresholds UNRESOLVED.  
- **Invented tolerance this pack:** **NONE**.
