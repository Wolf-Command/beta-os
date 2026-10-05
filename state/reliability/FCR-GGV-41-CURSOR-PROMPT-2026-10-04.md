# FCR-GGV-41

You are editing ONLY /Users/wolfterminal/beta-os. Do not commit, push, merge, reset, stash, or clean. Do not restart or reload Beta pid 93525. Do not signal production pid 15975 or Beta pid 93525. Do not touch close VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Do not open VDC-470e741f for write. Do not read or write state/bzg-daily-close/receipts/. Leave pid 63443 alone. Do not set BETA_AUTH_MODE. Do not hardcode any email or person id. Do not put secrets or process command lines in any file.

## This slice only

Parent requirement, exact name: Receipt field: currency
Id: FCR-GGV-41

GGV receipt confirm already keeps vendor, amount, tax, transaction date, category, account, and notes. There is no currency field and no currency assertion. Add the receipt currency field on the existing accounting row and a real assertion that reads it back. Do not invent a currency. Missing currency stays blank, not a default code and not zero. Do not redo tax (FCR-GGV-40) or amount (FCR-GGV-39). Do not add a staff page. Do not add a serve_beta.py route unless the currency field cannot be stored without one, and even then do not reload Beta.

## Disk lock
Tests use a small temporary sqlite created by the existing schema helper, or a schema-only empty database. NEVER shutil.copy2, vacuum, or backup the live file /Users/wolfterminal/beta-os/catalog/content_library.sqlite. NEVER write under catalog/backups. NEVER write the live catalog. If the feature cannot be tested without copying that live file, stop and write the result as BLOCKED_DISK with no copy made.

## Tests
py_compile Python you edit. Run the new test.
Write state/reliability/FCR-GGV-41-RESULT-2026-10-04.md with files changed, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE, BLOCKED, or BLOCKED_DISK.
Do not claim PROVEN_COMPLETE, staff_ready, or human commissioned. Stop when the test has been run, or immediately if you would have needed the live catalog copy.
