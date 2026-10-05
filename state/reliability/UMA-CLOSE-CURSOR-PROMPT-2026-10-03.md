You are editing ONLY the Uma Blu Daily Close staff workflow in /Users/wolfterminal/beta-os on branch build/wolf-command-rebuild. The tree is already dirty. Tip was 0b0e50da410d7158777871ae240c7e757502f5d3. Do not commit. Do not push. Do not merge PR #1. Do not reset, stash, or clean. Do not restart Beta or any server. Do not touch production (port 8787, pid 15975). Do not signal pid 1237 or pid 63443. Code and tests only. HTML may change on disk. Python will not be live until a later controlled Beta-only reload that you must not perform.

Read state/reliability/UMA-CLOSE-2026-10-03-COMMISSIONING.md first. Do not put secrets, API keys, cookies, or process command lines in any file you write.

PROTECTED, read only, never update, delete, or rewrite:
- Close VDC-470e741f-d889-437a-9a40-1ec9c083fb95, its evidence, photos, audit, and exception WI-109e1683-4e57-4fc0-860f-24bfbaf42975.
- Receipt files under state/bzg-daily-close/receipts/, including unattached EVD-CLOSE-EDC-95A47735CCB3.jpg. Do not guess a bank for that photo.
- 2 Oct close VDC-da1b6621-b657-4444-bc7c-7161a0bf5b94.
- 28 Sep close VDC-4046a805-8c76-4439-8019-f879f3b49513.
Tests must use a temporary database. Tests must not write those close ids.

Fix Uma Blu Daily Close staff workflow. Do not rewrite the 3 Oct close row or its files.

1. EDC reader. scripts/core/bzg_close_vision.py extract_edc_receipt calls _edc_prompt_with_bank_context which is not defined, so POST /api/venue-close/edc-receipt-extract returns 500 NameError before Gemini. Define the missing prompt helper or stop calling a missing name. Extraction must return EDC and QRIS separately. Staff confirms or edits. The original photo stays. Manual entry stays forever. A provider failure must be a soft staff message, never a raw NameError or provider string.

2. Cash evidence. Add Take photo and Upload photo on the cash section. Bind to outlet, business date, close, closer, declared count, timestamp. OCR is not required. An optional photo must not block submit.

3. Staff language. Remove the staff-facing word Reconcile. Wolf compares automatically as values are confirmed. Staff sees only: MATCH, DIFFERENCE FOUND, RECEIPT MISSING, CHECK THIS AMOUNT, PLEASE RECOUNT CASH, NOT USED TODAY, NEEDS MANAGER REVIEW. Finance and admin views may keep technical words.

4. Submit UX. The button must show SUBMITTING, then exactly one of CLOSE COMPLETE, CLOSE SAVED WITH EXCEPTION, or CANNOT SUBMIT plus a plain reason. Disable the button while the request is in flight. Repeated taps and refresh must not write another cash row. Tonight wrote declared_cash ten times and till_z_report four times for the same 3225000. Make declare/submit idempotent for the same close and same amount. Do not multiply totals. The 125000 gap is till and printed receipt versus live ESB, not a simple shortage. The result text must say the three sources separately: live ESB 3350000, printed receipt 3225000, till 3225000.

5. Three sources stay separate forever: live ESB, printed shift receipt, physical till and terminal slips. Do not overwrite one with another. Show source, amount, and difference. Mandiri example: ESB card 1915000, terminal 2040000, difference 125000. BRI QRIS: ESB 365000, terminal 1695000, difference 1330000.

6. Three bank cards from configuration: Mandiri, BNI, BRI. Each has ESB expected EDC, shift-report EDC if present, terminal EDC, difference, and the same four for QRIS, plus evidence and status. Not used today when confirmed zero. Do not guess a bank for the unattached photo. BNI was not stored on this close; do not invent BNI amounts.

7. Variance: do not force the user to change cash to match ESB. Show PLEASE RECOUNT CASH, then CONFIRM RECOUNT, then SUBMIT WITH EXCEPTION if still different. Route the exception through find_hfb_assignee / assignment, never a hardcoded person. Owner can take over. Do not change the existing 3 Oct exception.

8. Phone layout. No raw codes in staff UI (EDC_BRI, staff_ready, PERS-). No horizontal overflow. The huge date header stays.

9. Do not restart Beta. Do not reload the running process.

Tests must prove all of the following, and the test run must not write the protected close id:
- the missing function no longer 500s with NameError
- duplicate declare does not add a second cash total
- staff HTML has no Reconcile button
- a cash photo control exists
- the three cash sources are labeled
- protected close id VDC-470e741f-d889-437a-9a40-1ec9c083fb95 is not written by the tests

py_compile the Python files you edit. Write state/reliability/UMA-CLOSE-REPAIR-RESULT-2026-10-03.md with files changed, tests run and results, what you deliberately did not change, and status IMPLEMENTATION_DONE or BLOCKED. Do not claim HUMAN PASS. Stop when the fixes are saved and the tests have been run.
