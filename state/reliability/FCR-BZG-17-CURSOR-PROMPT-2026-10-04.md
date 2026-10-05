# FCR-BZG-17

You are editing ONLY /Users/wolfterminal/beta-os. Do not commit, push, merge, reset, stash, or clean. Do not restart or reload Beta pid 93525. Do not touch production port 8787 pid 15975. Do not touch closes VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Leave cursor-agent pid 63443 alone. Do not set BETA_AUTH_MODE. Do not hardcode any email or person id. Do not put secrets or process command lines in any file.

## This slice only

Parent requirement, exact name: Wrong-date protection
Id: FCR-BZG-17

The page already pins today's business date. That text is not protection. A close for one business date must reject data, a capture, or a submit that belongs to a different business date. Do not copy one day's ESB totals or receipt onto another day's close. A wrong-date attempt is rejected and leaves the target close unchanged.

Do not redo refresh/idempotency (FCR-BZG-16), the reopen chain (FCR-BZG-12), fingerprint freeze, history, petty cash, or bank import. No new HTTP surface unless the existing capture/submit path cannot reject without it. Prefer the existing venue-close functions. No Beta reload.

Actor comes from the existing caller. No hardcoded person.

## Tests
Temporary database or a copy only. Never write catalog/content_library.sqlite. Never update the two protected close ids.
Prove a wrong-date capture or submit is rejected and the target close row is unchanged. Also prove a same-date action is not rejected as a wrong date.
py_compile Python you edit. Run the new test.
Write state/reliability/FCR-BZG-17-RESULT-2026-10-04.md with files changed, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE or BLOCKED.
Do not claim PROVEN_COMPLETE, staff_ready, or human commissioned. Stop when the test has been run.
