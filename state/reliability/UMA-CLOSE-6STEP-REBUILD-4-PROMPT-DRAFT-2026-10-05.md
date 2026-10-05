# DRAFT — NOT ARMED (needs Owner approval: exceeds the 3-cycle limit)
# UMA-CLOSE-6STEP-REBUILD-4 — use human-edited shift figures downstream

Read REBUILD-1/2/3 prompts + EVIDENCE-ISOLATION-1. All hard rules unchanged.

Peaches' independent rendered acceptance of REBUILD-3 (14:34–14:40 WITA, WebKit iPhone 14, isolated copy, zero live writes):
29 Sep PASSED end to end (incl. idempotent exception submit with Expected Rp4.420.000 / Short Rp20.000).
3 Sep FAILED:
1. After EDIT → SAVE (`/save-shift-figure-edits` 200) → YES (`/confirm-shift-figures` 200) with BNI EDC 2,000,000 / QRIS 100,000, BRI EDC 3,000,000 / QRIS 500,000, cash 3,000,000, the bank step still shows "BNI — not used / BRI — not used" and the cash step shows "Shift report cash —" and "EXPECTED CASH —". The human-corrected confirmed figures must drive bank expectations (`wizard_bank_cards` / `_shift_expected_by_bank`), cash expected, review and submit — the latest confirmed human correction wins over raw read and owner-typed source, with provenance kept.
2. Because the banks are treated as "not used", a fresh page resumes 3 Sep straight to cash and the 4 FOUND CARD SLIPS (shown once after YES) are skipped. Once the banks have expected amounts, the step must require/offer receipts, and found slips must stay offered until used or explicitly marked not needed.
3. Minor: Search-date list shows 29 Sep "INCOMPLETE · Protected | REVIEW" while Missing closes shows "CONTINUE" (and the list isn't refreshed after submit); after an empty read the message says "Figures read — confirm they match" (should say "Nothing read").
Acceptance: same as REBUILD-3 — 29 Sep stays green; 3 Sep: EDIT figures → banks BNI/BRI expected from edits → USE THIS RECEIPT for found slips → cash expected = float + edited cash − petty OUT + petty IN → review → submit on copy → one result.
