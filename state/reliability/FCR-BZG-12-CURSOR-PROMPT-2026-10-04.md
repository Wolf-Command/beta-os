# FCR-BZG-12

You are editing ONLY the Beta workspace at /Users/wolfterminal/beta-os. Do not commit. Do not push. Do not merge. Do not reset, stash, or clean. Do not restart Beta or production. Do not touch production (port 8787, pid 15975). Do not signal beta pid 93525. Do not touch close VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Leave cursor-agent pid 63443 alone. Do not run recover-watchdog. Do not set BETA_AUTH_MODE. Do not hardcode any email or person id. Do not put secrets, API keys, cookies, or process command lines in any file you write.

## This slice only

Parent requirement, exact name: Reopen completed close with ORIGINAL → REOPEN EVENT → CHANGES → NEW APPROVAL
Id: FCR-BZG-12

Existing reopen of a VERIFIED_CLOSED row freezes a copy into venue_close_final_history and sets the working row OPEN. That freeze is not the four-stage chain. Build the missing chain on the existing venue-close path. Do not build a second close system. Do not redo history, cancel, petty cash, bank import, or any other FCR row.

Required stages, in this order, on a throwaway close only:
1. ORIGINAL — the completed close stays immutable in the existing final-history freeze. Do not edit that frozen original.
2. REOPEN EVENT — a distinct recorded event that points at that original, with reason, the caller as actor, and a time. Actor comes from the existing assignment path. No hardcoded person.
3. CHANGES — later edits apply only to the working close and are recorded as changes after the reopen event. They must not alter the original freeze.
4. NEW APPROVAL — a separate approval after those changes. The reopen event itself is not the new approval. The original freeze stays unchanged after approval.

## Tests
Use a temporary database or a copy. Never write catalog/content_library.sqlite. Never update the two protected close ids above.
py_compile Python you edit. Run the new test. Write state/reliability/FCR-BZG-12-RESULT-2026-10-04.md with files changed, test command and pass/fail counts, what you deliberately did not change, and status IMPLEMENTATION_DONE or BLOCKED.
Do not claim PROVEN_COMPLETE, staff_ready, human commissioned, or HUMAN PASS. Stop when the test has been run.
