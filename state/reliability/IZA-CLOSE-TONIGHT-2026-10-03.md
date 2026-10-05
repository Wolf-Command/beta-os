# IZA-CLOSE-TONIGHT-2026-10-03

**Status:** READY FOR HUMAN TEST
**Not** HUMAN PASS. staff_ready stays false. Iza has not done the close.

**Beta URL:** https://beta.wolfcommand.net/uma-blu-close
**Route:** `/uma-blu-close` (serves `dashboards/uma-blu-close.html`)
**Business date:** 2026-10-03 (Asia/Makassar). The page pins `todayWITA()` to that zone. Not 2026-10-02.

## Iza chain (catalog content_library.sqlite, read-only)

- Person PERS-IZA ACTIVE
- Auth identity AUTH-IZA-EMAIL (email provider, ACTIVE, bound to PERS-IZA). Email not copied here.
- Assignment ASG-IZA-CAPTAIN-UMA-1 ACTIVE, primary, no end date
- Position POS-BZG-CAPTAIN-UMA-1, role ROLE-BZG-CAPTAIN, label Floor Captain · Uma Blu, brand BZG-UMA, ACTIVE
- Scope SCOPE-BZG-UMA ACTIVE, target brand BZG-UMA
- Roster VCR-UMA-2 ACTIVE, assignment ASG-IZA-CAPTAIN-UMA-1, brand BZG-UMA
- `person_authorised_for_venue_close(PERS-IZA)` → allowed, reason closer_roster, role ROLE-BZG-CAPTAIN
- `venue.close.read` and `venue.close.submit` on Uma → allowed
- Banks ACTIVE: BANK-BZG-UMA-MANDIRI, BANK-BZG-UMA-BNI, BANK-BZG-UMA-BRI

Unsigned loopback GET `/uma-blu-close` returns 403 `authz_reason=anonymous` and "This close is not on your assignment." That is the anonymous gate. It is not Iza's roster. Nobody impersonated her.

## ESB today

Authorised same-day pull `esb_ingest.py --date 2026-10-03` finished 18:47 WITA. Upserts sales=54.

`snapshot_day('2026-10-03')` branch BLZ: incomplete false, finished_count 43, cancelled 4, max_pulled_at 2026-10-03T18:47:27+08:00. Payment names present: CASH, EDC MANDIRI, QRIS MANDIRI, EDC BRI, QRIS BRI. No BNI line in that pull. This is mid-service, not the final night figure. Her Pull ESB on the close live-pulls that date again and will not copy 2026-10-02. Preserved close VDC-87202768-55af-4c8e-abc3-382a5496b8c6 remains 2026-10-02 DATA_CAPTURED PERS-MATT.

## What was changed

- `dashboards/uma-blu-close.html` — Makassar business date; Take Photo / Upload Photo; phone layout; staff copy
- `scripts/core/bzg_daily_close.py` — shift receipt before "Not used today"; one CURRENT receipt per bank; omitted/zero bank after a confirmed shift report is Not used today (no photo); supersede excluded from totals
- `scripts/tests/test_bzg_daily_close_bank_supersede_20261003.py` — temp DB only
- `scripts/tests/test_bzg_daily_close_multi_edc_vision_1.py` — duplicate Mandiri no longer required to count twice
- serve_beta.py not edited. Owner cockpit, GGV, P2P not edited.

## Proof

- py_compile: bzg_daily_close.py, venue_close.py, owner_cockpit.py, serve_beta.py clean before reload
- `test_bzg_daily_close_bank_supersede_20261003.py` pass=15 fail=0 (one CURRENT Mandiri, TOTAL_EDC equals one receipt, superseded kept, BRI explicit 0/0 not used, no photo)
- Beta reloaded via LaunchAgent `net.wolfcommand.serve-beta` only. Old pid 84487. New pid 1237. Health GET http://127.0.0.1:8788/api/health → 200 `{"ok":true,"root":"beta-os"}`. Prod pid 15975 still on 127.0.0.1:8787.

## Phone layout actually checked (no device screenshot)

- viewport `width=device-width, initial-scale=1`
- body max-width 480px, overflow-x clip, box-sizing border-box, buttons width 100% and min-height 44px
- under 420px, photo actions stack to one column and the two-column row becomes one column
- ESB line grid uses minmax(0, …) so it can shrink
- Take Photo and Upload Photo are separate buttons on the shift receipt and on the bank receipt
- Provider names are not shown; a sanitizer strips gemini/openai/claude-style errors
- Owner panel text still contains ROLE-MATT, hidden until owner controls
- One honesty sentence no longer says Alchemist or Wolf

## What Iza must still do herself

Open https://beta.wolfcommand.net/uma-blu-close on her phone while signed in through Cloudflare. Open today's close (2026-10-03), pull ESB (the 18:47 figures will have moved), photograph the printed shift receipt, photograph Mandiri and BRI if they were used, leave BNI as not used if it is still zero, count cash, then submit. That human pass is not claimed here.
