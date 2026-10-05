# FCR-BZG-18

You are editing ONLY /Users/wolfterminal/beta-os. Do not commit, push, merge, reset, stash, or clean. Do not restart or reload Beta pid 93525. Do not touch production port 8787 pid 15975. Do not touch closes VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Leave cursor-agent pid 63443 alone. Do not set BETA_AUTH_MODE. Do not hardcode any email or person id. Do not put secrets or process command lines in any file.

## This slice only

Parent requirement, exact name: Full audit trail
Id: FCR-BZG-18

Close actions already call audit.safe_record in fragments. That is not a full trail. On the existing venue-close path, one close must be able to return its audit trail in order: action, actor from the caller, time, and the before/after that was recorded. Do not build a second audit system. Do not delete or rewrite old audit rows. Do not cover GGV, petty cash, or bank import.

Do not redo wrong-date protection (FCR-BZG-17), refresh/idempotency (FCR-BZG-16), or the reopen chain (FCR-BZG-12). No Beta reload. No new staff page.

## Tests
Temporary database or a copy only. Never write catalog/content_library.sqlite. Never update the two protected close ids.
On a throwaway close, perform at least open plus one later mutation, then read the trail and show those actions in order with actor and time. A missing step fails the test.
py_compile Python you edit. Run the new test.
Write state/reliability/FCR-BZG-18-RESULT-2026-10-04.md with files changed, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE or BLOCKED.
Do not claim PROVEN_COMPLETE, staff_ready, or human commissioned. Stop when the test has been run.
