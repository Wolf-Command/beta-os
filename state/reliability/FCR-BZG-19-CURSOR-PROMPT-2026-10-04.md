# FCR-BZG-19

You are editing ONLY /Users/wolfterminal/beta-os. Do not commit, push, merge, reset, stash, or clean. Do not restart or reload Beta pid 93525. Do not touch production port 8787 pid 15975. Do not touch closes VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Do not read or write files under state/bzg-daily-close/receipts/. Leave cursor-agent pid 63443 alone. Do not set BETA_AUTH_MODE. Do not hardcode any email or person id. Do not put secrets or process command lines in any file.

## This slice only

Parent requirement, exact name: Original evidence preservation
Id: FCR-BZG-19

File presence is not a preservation workflow. On the existing venue-close evidence path, attaching later evidence must not delete or overwrite the original evidence row or its stored bytes. The close may point at the later evidence as current. The original stays readable, including after a supersede. Do not build a second evidence store. No new staff page.

Do not redo the audit trail (FCR-BZG-18), wrong-date protection, idempotency, or the reopen chain. Do not reconcile ESB cash against a printed receipt and do not invent a cause for any difference. No Beta reload.

## Tests
Temporary database and temporary files only. Never write catalog/content_library.sqlite. Never update the two protected close ids. Never touch state/bzg-daily-close/receipts/.
On a throwaway close, store original evidence, then store a later item. Assert the original row and bytes are still readable and were not overwritten. Assert the later item can be current.
py_compile Python you edit. Run the new test.
Write state/reliability/FCR-BZG-19-RESULT-2026-10-04.md with files changed, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE or BLOCKED.
Do not claim PROVEN_COMPLETE, staff_ready, or human commissioned. Stop when the test has been run.
