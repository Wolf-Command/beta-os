# FCR-BZG-16

You are editing ONLY /Users/wolfterminal/beta-os. Do not commit, push, merge, reset, stash, or clean. Do not restart Beta or production. Do not touch production port 8787 pid 15975. Do not signal or reload Beta pid 93525. Do not touch closes VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Leave cursor-agent pid 63443 alone. Do not set BETA_AUTH_MODE. Do not hardcode any email or person id. Do not put secrets or process command lines in any file.

## This slice only

Parent requirement, exact name: Refresh/idempotency protection
Id: FCR-BZG-16

The parent says this row has no named prove. It is not the fingerprint-freeze rule (that is FCR-BZG-09). Do not redo the reopen chain (FCR-BZG-12). Do not redo history, cancel, takeover, or petty cash.

Build refresh/idempotency protection on the existing venue-close path:
- Repeating the same open, capture, cash declare, or staff submit for the same close must return the existing result and must not create a second current close, a second cash evidence row, or a second approval.
- A same-amount re-declare stays one declaration.
- A different amount is not silently treated as the same submission.
- Actor comes from the existing caller/assignment path. No hardcoded person.

## Tests
Temporary database or a copy only. Never write catalog/content_library.sqlite. Never update the two protected close ids.
py_compile Python you edit. Run the new test.
Write state/reliability/FCR-BZG-16-RESULT-2026-10-04.md with files changed, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE or BLOCKED.
Do not claim PROVEN_COMPLETE, staff_ready, or human commissioned. No Beta reload. Stop when the test has been run.
