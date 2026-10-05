# FCR-GGV-38

You are editing ONLY /Users/wolfterminal/beta-os. Do not commit, push, merge, reset, stash, or clean. Do not restart or reload Beta pid 93525. Do not touch production port 8787 pid 15975. Do not touch closes VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Do not read or write state/bzg-daily-close/receipts/. Leave pid 63443 alone. Do not set BETA_AUTH_MODE. Do not hardcode any email or person id. Do not put secrets or process command lines in any file.

## This slice only

Parent requirement, exact name: Receipt field: upload date
Id: FCR-GGV-38

GGV receipt confirm already keeps vendor, amount, transaction date, category, account, and notes. It has no upload date. Add upload date on the existing ggv receipt accounting row. Upload date is when Wolf stored the receipt. It is not the transaction date. Do not derive it by scanning the live receipt vault. Do not add tax, currency, or a new staff page. Do not build a second pipeline.

Do not redo FCR-BZG-12, 16, 17, 18, 19, 22, 23, or 28. Do not reconcile ESB cash against a printed receipt. Do not invent a cause for any cash difference. Do not collapse live ESB, printed receipt, and till into one number. A missing BNI line and a failed extract stay absent. They are not stored as zero. No Beta reload.

## Tests
Temporary database only. Never write catalog/content_library.sqlite. Never update the two protected close ids. Never touch state/bzg-daily-close/receipts/.
On a throwaway GGV receipt row, set a transaction date and a different upload date. Read the row back and assert they stay distinct. Assert a confirm that sends a transaction date does not overwrite the upload date.
py_compile Python you edit. Run the new test.
Write state/reliability/FCR-GGV-38-RESULT-2026-10-04.md with files changed, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE or BLOCKED.
Do not claim PROVEN_COMPLETE, staff_ready, or human commissioned. Stop when the test has been run.
