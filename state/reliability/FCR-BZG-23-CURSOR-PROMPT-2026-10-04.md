# FCR-BZG-23

You are editing ONLY /Users/wolfterminal/beta-os. Do not commit, push, merge, reset, stash, or clean. Do not restart or reload Beta pid 93525. Do not touch production port 8787 pid 15975. Do not touch closes VDC-470e741f-d889-437a-9a40-1ec9c083fb95 or VDC-87202768-55af-4c8e-abc3-382a5496b8c6. Do not read or write state/bzg-daily-close/receipts/. Leave pid 63443 alone. Do not set BETA_AUTH_MODE. Do not hardcode any email or person id. Do not put secrets or process command lines in any file.

## This slice only

Parent requirement, exact name: Mandiri / BNI / BRI outlet configuration
Id: FCR-BZG-23

A catalog read of three bank names is not a configuration workflow. On the existing outlet-bank table, an outlet with no bank rows is NEEDS CONFIGURATION. Configuring Uma Blu's settlement banks stores MANDIRI, BNI, and BRI as three separate ACTIVE rows for that outlet. It does not invent a fourth bank, merge the three, or mix EDC with QRIS. Reading the config back returns those three labels and does not write any other outlet.

Do not redo FCR-BZG-12, 16, 17, 18, 19, or 22. Do not reconcile ESB cash against a printed receipt. Do not invent a cause for any cash difference. Do not collapse live ESB, printed receipt, and till into one number. No new staff page. No Beta reload.

## Tests
Temporary database only. Never write catalog/content_library.sqlite. Never update the two protected close ids. Never touch state/bzg-daily-close/receipts/.
Assert an empty outlet is NEEDS CONFIGURATION. Assert configuration creates exactly MANDIRI, BNI, and BRI as separate ACTIVE rows. Assert a second read does not add a duplicate row.
py_compile Python you edit. Run the new test.
Write state/reliability/FCR-BZG-23-RESULT-2026-10-04.md with files changed, test command, pass/fail counts, what you did not change, and status IMPLEMENTATION_DONE or BLOCKED.
Do not claim PROVEN_COMPLETE, staff_ready, or human commissioned. Stop when the test has been run.
