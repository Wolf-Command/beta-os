# FCR-BZG-22

You are editing ONLY /Users/wolfterminal/beta-os. Do not commit, push, merge, reset, stash, or clean. Do not restart or reload Beta pid 93525. Do not touch production port 8787 pid 15975. Do not touch closes VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Do not read or write state/bzg-daily-close/receipts/. Leave pid 63443 alone. Do not set BETA_AUTH_MODE. Do not hardcode any email or person id. Do not put secrets or process command lines in any file.

## This slice only

Parent requirement, exact name: Unknown receipt lines preserved (not discarded)
Id: FCR-BZG-22

The parent has no prove for this. A shift-receipt parse must keep lines that match no known label. Those lines stay readable after parse, with their raw label and value, classified as needing classification. They are not dropped and not rewritten into a known total. Known lines may still be classified. Do not call a live vision provider. Do not build a second parser. No new staff page.

Do not redo FCR-BZG-12, 16, 17, 18, or 19. Do not reconcile ESB cash against a printed receipt. Do not invent a cause for any cash difference. Do not collapse live ESB, printed receipt, and till into one number. No Beta reload.

## Tests
Temporary database and temporary fixture text only. Never write catalog/content_library.sqlite. Never update the two protected close ids. Never touch state/bzg-daily-close/receipts/.
Parse a fixture that contains one known line and one unknown line. Assert the unknown line is still present with its raw text. Assert the known line was not replaced by the unknown line.
py_compile Python you edit. Run the new test.
Write state/reliability/FCR-BZG-22-RESULT-2026-10-04.md with files changed, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE or BLOCKED.
Do not claim PROVEN_COMPLETE, staff_ready, or human commissioned. Stop when the test has been run.
