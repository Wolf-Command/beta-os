# PETTY-IZA-FAIL-REPAIR

Human fail on Beta Captain Petty Cash OUT. Do not commission. staff_ready=false. human_commissioned=false. Do not raise any God Mode score. Do not hardcode Iza. Do not hardcode Rp55,000. Do not mutate close VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Do not restart Production (pid 1297). Do not commit or push. Do not change Cloudflare. Beta only.

Iza Zainatulloh Hulhidayati, Floor Captain, opened Uma Blu Petty Cash on a phone and failed. Three defects:

1. Outlet is a dropdown. She must not choose Pool Bar, Rainforest, or any other outlet. Derive outlet from authenticated person → assignment → scope → active workspace. For Uma Blu Petty Cash the outlet is Uma Blu, shown locked, not editable. Server rejects a client-supplied outlet that is not her authorised scope. Hiding the dropdown is not enough.

2. Remove accounting mapping / GL from the Captain form. She records only: amount, operational category, reason, optional payee, receipt/evidence. Person, business, outlet, business date/time, and direction OUT are known. Direction stays OUT. Captain cannot record IN. If an approved category→GL map exists, apply it downstream. If not, mark NEEDS ACCOUNTING CLASSIFICATION and still save the operational movement. Do not show GL codes to the Captain.

3. Category options must be operational language from the real approved category master if one exists. Do not invent a new list if a canonical one is already in the repo. Do not use A&G GL labels as the Captain category.

4. Current balance showed Rp0 (human-supplied opening). That is wrong. Reconcile the real Uma Blu petty chain from Alchemist history, existing Beta/Wolf petty rows, historical ledger, notas, receipts, Owner-supplied totals, and the two notas Iza already entered. Preserve provenance. If the chain supports Rp55,000, show that derived balance. If it does not, show the exact gap and do not force 55000. Do not write a fake opening.

Known Owner context, do not write these onto the protected 3 Oct close: 3 Oct morning opening Rp560,000; recorded OUTs already in the system; 3 Oct night top-up Rp500,000 as its own movement; 4 Oct morning opening Rp505,000. Implied OUT total Rp555,000 must be verified. Owner's stated current position after Iza's later entries is Rp55,000. Reconcile. Do not force.

5. Find Iza's two real notas. Do not ask her to re-enter them. If persisted, count each once. Do not duplicate them.

6. Captain phone screen, in order: PETTY CASH, Uma Blu, current balance, today's cash out, then amount, category, reason, optional payee, receipt photo, RECORD CASH OUT. Below that a simple ledger: amount, reason, category, person, time, receipt status, exception state. Finance/Owner can see accounting elsewhere. Captain view stays operational.

7. A legitimate same-day OUT changes expected closing cash exactly once: opening + cash sales + authorised cash IN − authorised petty OUT. Do not double count. Do not rewrite the 3 Oct close. Prove on a new current-date path.

8. Security tests, not hardcoded to Iza: assigned Captain can OUT her outlet; cannot IN; cannot choose or POST another outlet; cannot set GL; cannot delete or edit history; cannot move bank money; missing evidence is an exception not a fake complete; SoD holds; future Captains get this from role + assignment + scope.

Tests on a schema-only temp sqlite. No shutil.copy2 of the live catalog. No fake operational rows beyond what the reconciliation imports from a real source with provenance.

Reload Beta only if you must for the page to serve, and only the Beta listener (gui/501 net.wolfcommand.serve-beta). Leave prod 1297.

Write state/reliability/PETTY-IZA-FAIL-REPAIR-RESULT-2026-10-04.json and .md with: outlet lock proved, GL removed, balance derivation (amount, sources, gap vs 55000 or match), Iza's two notas found/not and counted once, daily-close once proved/failed, test pass/fail, beta pid, prod pid, protected close unchanged.

ready_for_human_test only if the phone workflow matches the spec and the balance is either reconciled to 55000 from sources or the exact unresolved difference is shown. Not human commissioned.
