# BZG-DAILY-CLOSE-TILL-EDC-1 RESULT

**As of:** 2026-10-02 WITA · **Branch:** `build/wolf-command-rebuild` (local only — no push)  
**Decision:** 2026-09-17 · PICK Uma Blu Daily Close (extend) + Owner order `BZG-DAILY-CLOSE-TILL-EDC-20261002`  
**Prod `:8787`:** READ-ONLY untouched (pid 15975 health 200)  
**Flags:** `staff_ready=false` · `human_commissioned=false`

## Goal

One reusable **BZG Daily Close** engine over `venue_close` — outlet config for all 7 Owner outlets; only Uma Blu human-activated; till + EDC evidence binding; no invented terminals/tolerances.

## What landed

### Single engine + registry-driven outlet config
- Module `scripts/core/bzg_daily_close.py` wraps/extends `venue_close` (not a greenfield close app)
- Migration `031_bzg_daily_close_till_edc` → `venue_close_outlet_config` + EDC/till evidence tables
- **7** config rows from Owner titles ↔ `org_outlet_registry`; title mismatches → **NEEDS CONFIGURATION**
- **Only `BZG-UMA`** has `human_close_enabled=1`; other outlets config-present, activation false
- Rainforest human open → `human_close_disabled`

### Till declare honesty
- `attach_declared_cash` / till-declare refuse `copy_from_esb` / `source=esb*` (`esb_copy_refused`)
- Till+Z path requires evidence `object_ref` or `content_hash` (`pos_z_report`)
- Declared ≠ verified honesty flags preserved
- Uma till float **Rp 1,000,000** from decisions.md 2026-08-02 citation; excluded-from-takings flag; no other floats invented

### EDC per-terminal evidence
- Tables `venue_close_edc_terminals` (empty) + `venue_close_edc_lines` (evidence-bound)
- Empty terminal registry → **NEEDS CONFIGURATION** visible in API + UI (no invented IDs)
- Orphan EDC amounts refused; Card Total = Σ EDC batch totals when present
- `esb_payments_are_not_edc_settlement: true`

### Variance / settlement / SoD
- Non-zero declared−ESB_CASH_FROM_PAYMENTS → `VARIANCE_REQUIRES_POLICY` → exception Work Item
- **0 ACTIVE** `venue_close_variance_policies` (Alchemist 2%/Rp5k soft warn **not** seeded)
- `settlement_api: UNAVAILABLE` · `settlement_status: PENDING_BANK`
- Exception title outlet-aware; HFB via Assignment/Role; SoD resolver≠verifier + submitter≠verifier
- **No `if Devi`**

### Mobile-first UX
- `dashboards/uma-blu-close.html` — max-width 480px; till+Z + EDC panels; config honesty banner
- Routes: `/uma-blu-close` + `/bzg/daily-close` on Beta `:8788` (CF Access → 403 unsigned / assignment gate — not 404)
- APIs: `/api/bzg/daily-close/overview`, `/api/venue-close/till-declare`, `/api/venue-close/edc-line`, `/api/venue-close/edc-terminals`

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_bzg_daily_close_till_edc_1.py` | **pass=57 fail=0** |
| `scripts/tests/test_uma_blu_daily_close.py` | **71 passed, 0 failed** |

## Commissioning honesty

- `staff_ready=false` · `human_commissioned=false`
- EDC terminal inventory remains **NEEDS CONFIGURATION** (STOP_FOR_OWNER for human commission completeness — eng honesty shipped)
- After Peaches credit-light verify: Devi real Uma close on Beta via Assignment seat — PASS/FAIL; not commissioned for scaffolding alone

## Telegram / discovery

- `TELEGRAM_SOURCE_INCOMPLETE` (Desktop chat) · procedure from Alchemist `/nightly` secondary source
- Gap matrix: `state/bzg-daily-close/GAP-VS-UMA-DAILY-CLOSE.md`

## Files

- `scripts/core/bzg_daily_close.py`
- `scripts/core/venue_close.py` (ESB-copy refuse, honesty, outlet-aware exception)
- `scripts/migrations/031_bzg_daily_close_till_edc.sql`
- `scripts/migrations/migrate_bzg_daily_close_till_edc_1.py`
- `scripts/serve_beta.py` (routes)
- `dashboards/uma-blu-close.html`
- `scripts/tests/test_bzg_daily_close_till_edc_1.py`
- `docs/canon/UMA-BLU-DAILY-CLOSE.md`

**Commit:** `8546cec` (local only — no push)

RESULT: **PASS** (engineering). Human commissioning PENDING.
