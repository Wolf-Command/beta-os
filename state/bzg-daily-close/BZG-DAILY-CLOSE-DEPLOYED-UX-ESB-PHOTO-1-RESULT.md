# BZG-DAILY-CLOSE-DEPLOYED-UX-ESB-PHOTO-1 RESULT

**As of:** 2026-10-02 WITA · **Branch:** `build/wolf-command-rebuild` (local only — no push)  
**Decision:** 2026-09-17 · PICK Uma Blu Daily Close (extend) + commissioning FAIL #2 pack  
**Prod `:8787`:** READ-ONLY untouched (pid `15975`)  
**Flags:** `staff_ready=false` · `human_commissioned=false`  
**Do not claim Iza-ready** — Peaches verifies deployed route; Matt then issues IZA RETEST READY.

## Root cause (verified)

`dashboards/uma-blu-close.html` at tip `a0cbc81` / feat `909addf` had **text** `photo://…` refs only — no `<input type="file" accept="image/*" capture="environment">`, no visible **Take Photo / Upload Photo**. Vision APIs existed; phone UX did not. Today’s ESB warehouse has **no BLZ rows** for 2026-10-02 — empty must surface as **ESB DATA UNAVAILABLE**, not zeros.

## What landed

### Phone Take / Upload Photo
- ESB closing receipt + each EDC receipt: **Take Photo** (`capture=environment`) + **Upload Photo** (library)
- Upload → `POST /api/venue-close/receipt-photo` → store under `state/bzg-daily-close/receipts/` (`close-receipt://…`) → vision draft → Looks Correct / Edit → confirm; original kept
- Preview + status line; hidden object_ref / content_hash (no typed `photo://` placeholders)

### Honest live ESB
- Capture for empty/missing day → `esb_data_unavailable` + message **ESB DATA UNAVAILABLE** (empty ≠ zero sales); no zero totals written
- Success returns `esb_live_status=AVAILABLE` + warehouse payment-lines source label (not settlement; not prior-day history)
- Open close auto-pulls live ESB; UI banner for UNAVAILABLE + Retry via Pull button
- Live warehouse today (2026-10-02): incomplete / empty → UNAVAILABLE path proven

### Dual source
- Live API snapshot + photographed closing receipt remain separate; mismatch still visible; no silent overwrite

## Deploy prove

| Check | Evidence |
| --- | --- |
| Beta `:8788` restart | launchctl kickstart `net.wolfcommand.serve-beta` → pid **55658** (was 51242) |
| Auth mode | `cloudflare_access` (prod-like) · `development_assertion_allowed=false` |
| Prod `:8787` | pid **15975** unchanged |
| HTML markers | Take Photo, Upload Photo, `capture=environment`, ESB DATA UNAVAILABLE, no `photo://` placeholder |
| Mobile viewport | phone 390×844 overflow=false; 4 photo buttons visible; shots under `docs/wolf/ops/shots/bzgclose-ux-photo1-*` |
| Auth HTML 200 | ephemeral `development_assertion` harness (Iza subject) — markers present |

## Tests

| Suite | Result |
| --- | --- |
| `scripts/tests/test_bzg_daily_close_deployed_ux_esb_photo_1.py` | **pass=48 fail=0** |
| `scripts/tests/test_bzg_daily_close_multi_edc_vision_1.py` | **pass=77 fail=0** |
| `scripts/tests/test_bzg_daily_close_till_edc_1.py` | **pass=57 fail=0** |
| `scripts/tests/test_uma_blu_daily_close.py` (empty-day UNAVAILABLE) | **pass (72)** |

## Files

- `dashboards/uma-blu-close.html`
- `scripts/core/bzg_daily_close.py` (receipt store/load)
- `scripts/core/venue_close.py` (ESB DATA UNAVAILABLE)
- `scripts/serve_beta.py` (`/api/venue-close/receipt-photo`)
- `scripts/tests/test_bzg_daily_close_deployed_ux_esb_photo_1.py`
- `scripts/audit/bzgclose_ux_photo1_shots.py`
- `scripts/tests/test_bzg_daily_close_till_edc_1.py` (fresh-day date avoid live taken close)
- `scripts/tests/test_uma_blu_daily_close.py` (UNAVAILABLE code)

**Commit tip:** `TIP_PENDING` (filled by stamp commit)

RESULT: **PASS** (engineering). `staff_ready=false`. Human commissioning PENDING — Peaches independent verify before IZA RETEST READY.
