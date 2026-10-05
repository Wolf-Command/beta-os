# UMA-CLOSE-4OCT-TAKEOVER

Iza's shift ended. Finish the existing 4 Oct Uma Blu close so Matt can take it over in the UI. Do not create a new close. Do not commission Daily Close.

## Same close
`VDC-64f5f529-5485-4ff1-a0cc-11941a64e6f5`
business_date 2026-10-04, outlet BZG-UMA, original closer PERS-IZA.
declared_cash_amount is NULL. Leave it NULL. Do not write 360000 into it.
Do not change esb_totals_json. Do not mutate VDC-470e741f or VDC-87202768.

## Display already partly fixed — keep it
ESB cash = cash_from_payments Rp360,000, its own line.
Finished bills = 61, its own line, never under Difference or cash.
Difference stays "Cannot calculate yet" until a cash count exists.
Petty cash paid today = Rp451,000 (the two persisted OUTs, once).
Expected cash = configured till float Rp1,000,000 (venue_close_outlet_config, citation 2026-08-02, not the petty opening) + ESB cash 360,000 − petty OUT 451,000 = 909,000.
No GL, journals, outlet dropdown, or Reconcile button.

## Photo
Earlier engine save worked, but a local HTTP call without Cloudflare JWT got 403. That is not a phone proof.
On the served close page, Take Photo and Upload Photo must be real file inputs a phone can use (camera capture plus library upload).
Authenticated upload must store the original, bind it to this close, BZG, Uma Blu, 2026-10-04, the actor, and the time.
If reading the image fails, keep the photo and allow the numbers to be typed. No provider error on screen.
Add a regression test that finished-bills count cannot render inside the difference line.

## Owner takeover (permanent, not a one-off)
An Owner with assignment, role, scope, and permission can take over an unfinished close in the Wolf UI. No hardcoded email. No Peaches step.
Takeover of this close must keep the same close id, date, and outlet.
Audit must show: Iza started it; defects stopped her finishing during her shift; takeover actor; takeover time; reason "Iza shift ended / Owner takeover after workflow failure".
Do not erase her entries, the ESB snapshot, petty links, or timestamps.
Page must show: 4 October 2026, Uma Blu, Original closer Iza, Taken over by the current Owner.
After takeover the same page continues: shift report, banks, cash count, automatic petty, then one submit.

## Record the impact
Write a short incident note in state/reliability that the closer's shift ended before Wolf let the real close finish. This is a human commissioning fail, not a staff pass, even if the Owner later submits.

## Limits
Beta only. Do not restart prod pid 1297. Do not commit. Do not copy the live catalog. Reload Beta only if Python changed and 8788 has one listener.
Result file: state/reliability/UMA-CLOSE-4OCT-TAKEOVER-RESULT-2026-10-04.json
Include close id, photo input proof, display lines, takeover permission (not a hardcoded person), declared still null, protected close unchanged, beta pid, prod pid.
