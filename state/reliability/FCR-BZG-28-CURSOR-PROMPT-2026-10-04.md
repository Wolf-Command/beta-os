# FCR-BZG-28

You are editing ONLY /Users/wolfterminal/beta-os. Do not commit, push, merge, reset, stash, or clean. Do not restart or reload Beta pid 93525. Do not touch production port 8787 pid 15975. Do not touch closes VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Do not read or write state/bzg-daily-close/receipts/. Leave pid 63443 alone. Do not set BETA_AUTH_MODE. Do not hardcode any email or person id. Do not put secrets or process command lines in any file.

## This slice only

Parent requirement, exact name: Manual fallback if image extraction fails
Id: FCR-BZG-28

When receipt image extraction fails, the close must not be blocked and the failure must not become a zero amount or a confirmed extract. The caller can record the figures manually for that same slot afterward. A missing bank line, including BNI, stays absent. It is not stored as zero. Do not call a live vision provider. Do not build a second extractor. No new staff page.

Do not redo FCR-BZG-12, 16, 17, 18, 19, 22, or 23. Do not reconcile ESB cash against a printed receipt. Do not invent a cause for any cash difference. Do not collapse live ESB, printed receipt, and till into one number. No Beta reload.

## Tests
Temporary database and temporary fixture only. Never write catalog/content_library.sqlite. Never update the two protected close ids. Never touch state/bzg-daily-close/receipts/.
Force an extraction failure. Assert the result is a staff-safe failure, no zero amount was written, and a following manual figure is stored as manual entry rather than as a successful extract.
py_compile Python you edit. Run the new test.
Write state/reliability/FCR-BZG-28-RESULT-2026-10-04.md with files changed, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE or BLOCKED.
Do not claim PROVEN_COMPLETE, staff_ready, or human commissioned. Stop when the test has been run.
