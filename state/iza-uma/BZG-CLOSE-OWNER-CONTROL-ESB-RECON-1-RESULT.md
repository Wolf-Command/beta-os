# BZG-CLOSE-OWNER-CONTROL-ESB-RECON-1 RESULT

**As of:** 2026-10-02 WITA · **Branch:** `build/wolf-command-rebuild` (local only — no push)  
**Decision:** 2026-09-17 · PICK Uma Blu Daily Close (extend) + Owner pack OWNER-CONTROL-ESB-RECON-1  
**Prod `:8787`:** READ-ONLY untouched (pid `15975`)  
**Flags:** `staff_ready=false` · `human_commissioned=false` · `daily_close_commissioned=false` · Iza commissioning FAIL unchanged  
**Do not claim Matt-ready** — Peaches verifies; then one ping.

## Forensic (why 61 / 2,855,000 ≠ 58 / 2,735,000)

| Delta | Cause | Verified |
| --- | --- | --- |
| Bills +3 | Live Finished includes 3 OTHER COST bills (COMPLIMENT + Executife Chef ×2, `billNum=null`) omitted on printed closing receipt | Excl OTHER → **58 bills, pax 103, gross 18,395,000** |
| Cash +120,000 | Live sums **cash tendered** (payment lines); receipt cash = **cash-bill grandTotal**. Change overpay on 5 bills Σ Rp 120,000 | `cash_sales_grand` = **2,735,000** |
| Not TZ/cancel | All `biz_date=2026-10-02`; cancelled=5 separate | stamped |

**Policy:** sources kept — no overwrite. Stamp: `FORENSIC-ESB-RECON-20261002.md` (+ `.json`).

Bank EDC/QRIS (BNI/Mandiri) live method totals match receipt non-cash lines after classify-by-`paymentMethodName`.

## What landed

### A) Canonical Owner Control (Daily Close first)
- Permission `venue.close.owner_control` → **ROLE-MATT** only (assignment-derived; not email)
- Actions (reason + audit + work preserved; no money movement): unlock abandoned, override lock, return for correction, reopen, cancel, correct assignment
- Existing takeover/reassign kept (`venue.close.reassign`)
- UI Owner Control panel on `/uma-blu-close`
- Wolf-wide gap register (honest PARTIAL): `OWNER-CONTROL-GAP-REGISTER.json`

### B) Dual-source + bank-split recon
- `esb_close_snapshot`: classify QRIS/EDC from `paymentMethodName` (Uma TypeName=CARD bug fixed); `payments_by_bank_split`; cash tendered vs sales grand
- `recon_board`: captured expected kept; **dual_source** live vs closing receipt difference board + explanations; bank-split EDC/QRIS panels
- UI: `dualSourceBox` + `bankSplitBox`

## Deploy prove

| Check | Evidence |
| --- | --- |
| Beta `:8788` restart | launchctl kickstart → pid **65974** (was 62275) |
| Prod `:8787` | pid **15975** unchanged |
| Unsigned `/uma-blu-close` | **403** (auth gate) |
| Matt `venue.close.owner_control` | **True** via ROLE-MATT |
| Disk UI markers | Owner Control, dualSourceBox, bankSplitBox, Unlock abandoned |

## Tests

| Suite | Result |
| --- | --- |
| `test_bzg_close_owner_control_esb_recon_1.py` | **pass=47 fail=0** |
| `test_bzg_close_governed_takeover_1.py` | **pass=46 fail=0** |
| `test_bzg_daily_close_multi_edc_vision_1.py` | **pass=77 fail=0** |

## Files

- `scripts/core/esb_close_snapshot.py`
- `scripts/core/venue_close.py`
- `scripts/core/bzg_daily_close.py`
- `scripts/core/uma_devi_p0.py`
- `scripts/core/audit.py`
- `scripts/serve_beta.py`
- `scripts/migrations/migrate_bzg_close_owner_control_esb_recon_1.py`
- `dashboards/uma-blu-close.html`
- `scripts/tests/test_bzg_close_owner_control_esb_recon_1.py`
- `state/bzg-daily-close/FORENSIC-ESB-RECON-20261002.{md,json}`
- `state/bzg-daily-close/OWNER-CONTROL-GAP-REGISTER.json`

RESULT: **PASS** (engineering). `staff_ready=false`. Human: Peaches independent verify → then Matt ping (not claimed here).
