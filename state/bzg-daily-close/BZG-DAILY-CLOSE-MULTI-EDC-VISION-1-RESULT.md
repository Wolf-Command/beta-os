# BZG-DAILY-CLOSE-MULTI-EDC-VISION-1 RESULT

**As of:** 2026-10-02 WITA · **Branch:** `build/wolf-command-rebuild` (local only — no push)  
**Decision:** 2026-09-17 · PICK Uma Blu Daily Close (extend) + Owner order `BZG-DAILY-CLOSE-MULTI-EDC-VISION-20261002`  
**Prod `:8787`:** READ-ONLY untouched  
**Flags:** `staff_ready=false` · `human_commissioned=false`

## Goal

Extend canonical BZG Daily Close so Uma supports **0..N EDC receipts/day** with **separate EDC card + QRIS**, vision draft → human confirm, ESB closing receipt + live API dual-source, recon board, phone-first UX.

## What landed

### Multi EDC receipts (0..N)
- Table `venue_close_edc_receipts` — repeating Add; never require exactly one
- Each receipt: bank/acquirer (free-text OK), optional terminal, settlement date, `edc_card_amount`, `qris_amount`, total, image, batch/ref, OCR confidence, human confirm
- Aggregates: `TOTAL_EDC`, `TOTAL_QRIS`, `TOTAL_CARD_QRIS` — QRIS never merged into card
- Configured terminals = available options; unused terminals do **not** create placeholder rows
- Empty live terminal registry stays **NEEDS CONFIGURATION** (no invented TIDs)

### Vision draft ≠ accounting truth
- Module `scripts/core/bzg_close_vision.py` — Gemini Vision when key authorised; fixture/dry-run for tests
- Draft → **Looks Correct / Edit**; preserves extracted, confirmed, who, ts, image
- Low confidence: blank/flag; do not invent
- Append-only `venue_close_vision_events`

### ESB dual source
- `venue_close_esb_closing_receipts` — photo evidence required alongside live ESB API snapshot
- Mismatch → visible `api_mismatch`; **no silent overwrite** of API totals
- ESB snapshot classifies `qris_from_payments` separately from CARD

### Recon board + phone UX
- `/api/venue-close/{id}/recon-board` — cash / EDC / QRIS expected vs confirmed + evidence completeness
- `dashboards/uma-blu-close.html` phone-first: ESB receipt → Add EDC Receipt (repeat) → cash → recon
- Routes: edc-receipt-extract/confirm, esb-receipt-extract/confirm, edc-receipts, esb-receipts, recon-board

### Honesty preserved
- Only Uma `human_close_enabled`
- 0 ACTIVE variance policies / no invented tolerances
- `staff_ready=false` · `human_commissioned=false`
- Settlement API still UNAVAILABLE

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_bzg_daily_close_multi_edc_vision_1.py` | **pass=77 fail=0** |
| `scripts/tests/test_bzg_daily_close_till_edc_1.py` (regression) | **pass=57 fail=0** |

Covered: 1 receipt, 3 receipts, EDC-only, QRIS-only, both, unused configured terminal, image extraction, wrong extraction edited, low-confidence, ESB receipt extraction, API vs receipt mismatch, duplicate warning, totals, phone workflow, evidence/audit.

## Files

- `scripts/core/bzg_daily_close.py`
- `scripts/core/bzg_close_vision.py`
- `scripts/core/esb_close_snapshot.py` (QRIS separate)
- `scripts/migrations/032_bzg_daily_close_multi_edc_vision.sql`
- `scripts/migrations/migrate_bzg_daily_close_multi_edc_vision_1.py`
- `scripts/serve_beta.py`
- `dashboards/uma-blu-close.html`
- `scripts/tests/test_bzg_daily_close_multi_edc_vision_1.py`

**Commit:** `909addf` (local only — no push) · tip `dab1e99`

RESULT: **PASS** (engineering). Human commissioning PENDING (`staff_ready` stays false).
