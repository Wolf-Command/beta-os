# UMA BLU DAILY CLOSE — honesty table (Beta)

**Status:** BUILT + TESTED 2026-09-17 (Cursor Local Agent)  
**Run:** BF-uma-blu-daily-close-20260917  
**Scope:** Uma Blu (`BZG-UMA`) only · Beta only · ESB warehouse **read-only** · Habitat untouched  

| Capability | Status |
|------------|--------|
| `venue_daily_closes` + UNIQUE(entity, brand, date) | **BUILT** (`021_uma_blu_daily_close`) |
| ESB day fingerprint from `sales` / `salesPayments` | **BUILT** (`esb_close_snapshot.py`) |
| Cash basis | **ESB_CASH_FROM_PAYMENTS** (payment lines — not settlement) |
| Settlement API | **UNAVAILABLE** (Felix) |
| Declared till cash via Core Evidence | **BUILT** (`cash_count`, DECLARED ≠ VERIFIED) |
| Variance = declared − esb_cash_from_payments | **BUILT** (server-only) |
| Live variance threshold rows | **0** (never invent; non-zero → `VARIANCE_REQUIRES_POLICY`) |
| Live monetary authority | **0** (unchanged) |
| Clean path (variance 0 + fresh fingerprint) | **RECONCILED** then **VERIFIED_CLOSED** via SYSTEM |
| Exception Work Item → Head of F&B assignment | **BUILT** (role/scope — no `if Devi`) |
| HFB (`ROLE-BZG-HFB`) permissions | **exception resolve + verify only** — **not** `venue.close.submit` (do not widen overnight; closer still WAITING) |
| SoD: resolver ≠ sole verifier; submitter ≠ verifier on exception | **BUILT** |
| Closer role `ROLE-BZG-CLOSER` | **BUILT** — **WAITING FOR VERIFIED CLOSING OPERATOR** (no named person) |
| Submit grants | **ROLE-BZG-CLOSER** + **ROLE-MATT** only |
| Devi seed (`PERS-DEVI` / `deviputu236@gmail.com`) | **BUILT** (HR-authorised email) |
| API `/api/venue-close/...` | **BUILT** |
| UI `dashboards/uma-blu-close.html` | **BUILT** |
| Client totals / variance / state override | **REFUSED** (open/capture/declare/reconcile/exception/resolve/verify) |
| Habitat `content_planner` | **UNTOUCHED** |
| ESB / Production writes | **FORBIDDEN** |
| POS / Alchemist / ClickUp / other venues | **NOT IN SLICE** |

## BZG-DAILY-CLOSE-TILL-EDC-1 (2026-10-02)

Extends this engine — **not** a second close product. Outlet config for Owner’s 7 BZG outlets (registry-driven); **only Uma Blu** `human_close_enabled`. Till + Z-report evidence path; EDC per-terminal evidence (empty terminal registry = **NEEDS CONFIGURATION** — no invented IDs). Card Total = Σ EDC batches when present; ESB payments ≠ EDC settlement. Settlement API remains **UNAVAILABLE** / PENDING_BANK. No ACTIVE variance tolerance seeded (Alchemist 2%/Rp5k soft warn is not Wolf policy). Till float Rp 1,000,000 (Owner 2026-08-02) cited for Uma only. `staff_ready=false` · `human_commissioned=false` until Devi real-close PASS via Assignment/Role/Scope.

## States (strict)

`OPEN` → `DATA_CAPTURED` → `EVIDENCE_SUBMITTED` → `RECONCILED` → `VERIFIED_CLOSED` (variance 0, system)  
or → `VARIANCE_REQUIRES_POLICY` → `EXCEPTION` → `RESOLVED` → `VERIFIED_CLOSED`  

`SUBMITTED` ≠ `RECONCILED` ≠ `VERIFIED`  
`EXCEPTION` ≠ `RESOLVED` ≠ `VERIFIED_CLOSED`  
Declared cash ≠ verified cash.

## Honesty flags

```
settlement_api: UNAVAILABLE
esb_cash_basis: PAYMENT_LINES_NOT_SETTLEMENT
live_variance_threshold: 0
live_monetary_authority: 0
```

## Modules

- `scripts/core/venue_close.py`
- `scripts/core/esb_close_snapshot.py`
- `scripts/migrations/021_uma_blu_daily_close.sql` + `migrate_uma_blu_daily_close.py`
- `scripts/tests/test_uma_blu_daily_close.py`
- Decision: `2026-09-17 · PICK: Uma Blu Daily Close + Exception Handover` in `~/.openclaw/wolf-output/decisions.md`
