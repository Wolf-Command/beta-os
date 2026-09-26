# ATRIUM FINANCE — READY FOR HUMAN COMMISSIONING

27 Sep 2026. This is the ledger application on a fresh database. It is not commissioned until a person in each role below has signed in and checked their own screen.

## Start a fresh database

From `/Users/wolfterminal/atrium-finance`:

```
export SESSION_SECRET='(a long random value; do not commit it)'
export SEED_CONTROLLER_PASSWORD='(role password; do not commit it)'
export SEED_ACCOUNTANT_PASSWORD='...'
export SEED_FRONT_OFFICE_PASSWORD='...'
export SEED_PURCHASING_PASSWORD='...'
export SEED_GM_PASSWORD='...'
export SEED_AUDITOR_PASSWORD='...'
export PORT=8790
export DATABASE_FILE="$PWD/data/commissioning/atrium.sqlite"
zsh scripts/start-fresh-commissioning.sh
```

The script refuses port 8787 and port 8788. It refuses any database path under `data/uncommissioned/`. It refuses to start if any name above is empty. It refuses to open an existing database file unless `FRESH_DB_REUSE=yes`. The server creates the SQLite file on first boot. `*.sqlite` is gitignored.

Sign in at `http://127.0.0.1:8790` after it prints that it is listening.

## Backup

The atrium-finance nightly job is not configured. These names are unset: `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_ENDPOINT`. There is no `.env`. `scripts/com.atriumfinance.backup.plist` is not loaded. The screen still says no backup is recorded until that job uploads.

A separate scratch proof on 27 Sep 2026 used the existing rclone remote named `b2` (type b2). It uploaded one test database to `b2:wolf-cold-archive/atrium-finance-d5-scratch/atrium-d5-fresh.sqlite`, matched SHA1 `25e4b3d6689678c96052414989adf7e18fbfb4ca`, restored the file, and booted it on port 8792. That object is a test marker (`D5-SCRATCH-MARKER`), not the hotel's books and not the scheduled atrium backup. Do not point commissioning at it.

Do not use `data/uncommissioned/atrium.sqlite`. Do not import `data/owner_pool.json` or `data/owner_email_store.json`. Those files are an old generated sample (98 units), not the hotel's register.

The chart of accounts that appears on a new database is a USALI template. It is not last month's books. Posted journals, stock, staff, receivables, payables, and owners start empty. Empty screens say so.

Sign-in uses the email and password issued for the role. Google does not open a session. The first-boot addresses are below. A Financial Controller should replace them with the real mailbox for that role before anyone else relies on them.

| Role | First-boot email | What this role is for |
| --- | --- | --- |
| Financial Controller | controller@seed.invalid | Full control, including settings and who can sign in |
| General Accountant | accountant@seed.invalid | Drafts and the ledger. Cannot change administration |
| Front Office / Night Auditor | front-office@seed.invalid | Daily revenue. Cannot open the ledger, reports, tax, or administration |
| Accounts Payable & Purchasing Clerk | purchasing@seed.invalid | Purchasing, stock, and payables. Cannot open reports or post journals |
| General Manager / Hotel Owner | gm@seed.invalid | Read and export. Cannot edit or open administration |
| Internal & External Auditor | auditor@seed.invalid | Read the ledger and tax. Cannot change anything. Cannot open administration |

Passwords are whatever was set in `SEED_*_PASSWORD` before the first boot. They are not written in this file.

## Every role

1. Open the local app. Sign in with your role email and password.
2. Wrong password: you should see an error and stay on the sign-in screen.
3. Close the tab, open it again: you should still be signed in.
4. Open the user menu and choose Keluar / Kunci Sesi. You should be back on the sign-in screen. Refresh. You should still be signed out.
5. On a phone-width window, the page should not slide sideways off the screen, and the user menu should still open logout.

## Financial Controller

1. Command Centre should say the property profile is not set, and that there are no posted journals. You should not see a dollar total standing in for hotel revenue.
2. Administration → Period Closing Locks & Hotel Master Profile. The name is blank, rooms are 0, and the period lock is empty (books open). Type the real property name, room count, and currency. Save. Leave the lock date empty until you actually close a period.
3. Confirm the other five role accounts exist, and that each is attached to the role in the table above, not to a person's private rules. Creating a user starts with an empty password field. Type a password. The form does not fill one in.
4. Tax: the tax names are a list. Rates are not set. Enter a rate only when you know the rate that applies. Do not calculate tax before that.
5. Chart of accounts: review the template. It is a starting chart, not a statement of what the hotel earned.
6. Do not press anything that promises sample staff or sample owners. That action is turned off.

## General Accountant

1. You can open Operations, the journal workbench, the ledger, and tax.
2. Open Administration. You should see that this role cannot view it.
3. Revenue and spending lists say nothing is recorded, apart from anything a person has typed on purpose.
4. Enter a draft only from a real voucher. The amount line is in IDR. If you leave the amount blank, the preview says "Not entered".
5. You cannot approve your own way into administration settings.

## Front Office / Night Auditor

1. You can open Command Centre and Operations.
2. Open Administration, the journal list, or the chart of accounts. You should be refused.
3. Integrations → PMS night audit. The amount boxes are empty. Do not submit them until you are typing the night-audit sheet from the hotel. Submitting blanks is refused.
4. A draft you create is not posted history until a role that is allowed to approve and post has done that.

## Accounts Payable & Purchasing Clerk

1. You can open inventory, purchase orders, and payables.
2. Inventory should say no items are recorded and that no sample stock was loaded.
3. Payables should say nothing is outstanding.
4. Open Reports. You should be refused.
5. You should not be able to post a journal.

## General Manager / Hotel Owner

1. You can open Command Centre, Operations, the ledger, reports, and tax, to read them.
2. Command Centre should not show invented revenue. If nothing has been posted, it says so.
3. Owner Pool (under Reports) should say no units are recorded, unless someone has entered real units.
4. Open Administration. You should be refused.
5. You should not be able to save a revenue draft.

## Internal & External Auditor

1. You can open journals and tax rules to read them.
2. You should not be able to post revenue, delete a journal, or open Administration.
3. If a screen is empty, the report is empty. Do not treat a template chart or an unconfigured tax rate as a filed return.

## Not in this commissioning

- Do not move money, pay a vendor, or change a bank account as part of this test.
- Do not email owners. The old dispatch list is sample data.
- The atrium nightly backup waits until `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, and `B2_ENDPOINT` are set and `scripts/com.atriumfinance.backup.plist` is loaded. Until then the screen says no backup is recorded. That is true for this app. The scratch object under `atrium-finance-d5-scratch/` is not that job.
