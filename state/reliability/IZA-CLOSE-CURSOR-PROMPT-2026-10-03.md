You are editing ONLY the Uma Blu daily close lane in /Users/wolfterminal/beta-os (tip 0b0e50da, dirty tree). Do not commit, push, reset, clone, or merge. Do not restart any server. Do not edit owner cockpit files (owner_cockpit.py, owner_pulse_ro.py, owner-cockpit.html, test_owner_ro_loaders_20260930.py). Do not edit ggv finance files or P2P. Do not edit serve_beta.py unless a close route is actually missing; if you touch it, only the close route and say so. Do not mutate catalog rows. Do not touch close VDC-87202768-55af-4c8e-abc3-382a5496b8c6 (2026-10-02 DATA_CAPTURED PERS-MATT). Do not invent a Mandiri photo. Do not hardcode any email. Do not loosen RBAC. Do not set staff_ready. Do not claim HUMAN PASS.

Read the code first. Do not redo working pieces.

Already proved, leave the chain alone:
- Catalog content_library.sqlite: PERS-IZA ACTIVE, AUTH-IZA-EMAIL, ASG-IZA-CAPTAIN-UMA-1 primary ACTIVE, position POS-BZG-CAPTAIN-UMA-1 ROLE-BZG-CAPTAIN "Floor Captain · Uma Blu" brand BZG-UMA, scope SCOPE-BZG-UMA, roster VCR-UMA-2.
- person_authorised_for_venue_close resolves roster, not a hardcoded email.
- Outlet banks BANK-BZG-UMA-MANDIRI, BANK-BZG-UMA-BNI, BANK-BZG-UMA-BRI ACTIVE.
- capture_esb_snapshot refuses incomplete days (empty is not zero) and calls _refresh_esb_warehouse_for_date. Frozen snapshots are not overwritten by live ESB.
- Photo buttons and original-image upload exist. Staff vision errors are sanitized.

Fix these real gaps:

1. dashboards/uma-blu-close.html todayWITA() uses the device local calendar. Pin business date to Asia/Makassar (YYYY-MM-DD). The date control must show that business date, not a timestamp and not 2026-10-02.

2. bank_cards() in scripts/core/bzg_daily_close.py treats a missing expected map as EDC 0 and QRIS 0 and labels every configured bank NOT_USED_TODAY. That is wrong before a confirmed shift receipt. NOT USED TODAY only when the confirmed shift receipt (or a real captured ESB snapshot for this business date) explicitly has that bank at EDC 0 and QRIS 0. Then no terminal photo is required. Override "add receipt anyway" stays, with the existing audit. Unknown / not-yet-confirmed expected must say the shift receipt is still needed, not "not used".

3. After the shift receipt is confirmed, prepopulate Mandiri, BNI, and BRI EDC and QRIS from that receipt's payment lines (raw labels kept). EDC and QRIS stay separate. Zero difference = MATCH. Do not copy 2026-10-02 amounts.

4. One bank + one business date = one CURRENT reconciliation. Second photo of the same receipt must not increase TOTAL_EDC / TOTAL_QRIS. Corrected receipt: old evidence_role SUPERSEDED, counted_in_totals 0, evidence kept, new row CURRENT. A duplicate warning while both still count is a failure. confirm_edc_receipt currently stores the raw acquirer label; make supersede match the same normalized bank. Add a temp-db test next to the existing close tests that asserts: two confirms of the same bank/date/amounts leave exactly one CURRENT counted row and TOTAL equal to one receipt, superseded excluded. Also a test that a configured bank with confirmed EDC 0 and QRIS 0 is NOT_USED_TODAY and does not require a photo. Update test_bzg_daily_close_multi_edc_vision_1.py only if its "duplicate not deleted / count >= 4" assertion requires both copies to count; superseded history may remain, totals must not.

5. Extraction failure must not block the close: photo stored, plain language, manual entry, retry. No provider or model names in staff-visible HTML/JS strings. Unknown receipt lines stay NEEDS CLASSIFICATION with the raw label, not dropped.

6. Phone layout: viewport is present; keep overflow-x contained, buttons full-width-friendly, no horizontal scroll from fixed widths. Staff-visible copy must not show internal ids (close_id, PERS-, ROLE-, vision event ids) or raw provider errors. Owner controls stay owner-only. Do not turn the page into a Peaches prompt.

7. Do not create a second close for takeover, cancel, or reopen. Do not change permission grants.

Run the new test and the existing close test you touch. py_compile the py files you edit. Write state/reliability/IZA-CLOSE-TONIGHT-2026-10-03.md with: files changed, tests run and results, what you deliberately did not change, and status IMPLEMENTATION_DONE (not READY, not HUMAN PASS). The parent will set READY or BLOCKER after ESB and reload proof.

Stop when those fixes are saved and tests have been run.
