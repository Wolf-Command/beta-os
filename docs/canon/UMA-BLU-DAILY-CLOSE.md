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
| Clean path (variance 0 + fresh fingerprint) | **VERIFIED_CLOSED** via SYSTEM |
| Exception Work Item → Head of F&B assignment | **BUILT** (role/scope — no `if Devi`) |
| SoD: resolver ≠ sole verifier | **BUILT** |
| Closer role `ROLE-BZG-CLOSER` | **BUILT** — **WAITING FOR VERIFIED CLOSING OPERATOR** (no named person) |
| Devi seed (`PERS-DEVI` / `deviputu236@gmail.com`) | **BUILT** (HR-authorised email) |
| API `/api/venue-close/...` | **BUILT** |
| UI `dashboards/uma-blu-close.html` | **BUILT** |
| Client totals / variance / state override | **REFUSED** |
| Habitat `content_planner` | **UNTOUCHED** |
| ESB / Production writes | **FORBIDDEN** |
| POS / Alchemist / ClickUp / other venues | **NOT IN SLICE** |

## States (strict)

`OPEN` → `DATA_CAPTURED` → `EVIDENCE_SUBMITTED` → (`VERIFIED_CLOSED` if variance 0)  
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
