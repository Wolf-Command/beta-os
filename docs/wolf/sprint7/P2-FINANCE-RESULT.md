# P2 — Atrium Finance staff readiness — 27 Sep 2026

Branch `wolf/foundation-20260926` in `/Users/wolfterminal/atrium-finance`. Not pushed. Production `:8787` stayed on pid 15975. Beta `:8788` stayed on pid 47662. The proof server was a separate process on `:8790` with a scratch database under `/tmp/atrium-sprint7-20260927/`. That process was stopped after the checks.

ENGINEERING PASS on a fresh database. Staff can start human commissioning of the ledger. Offsite backup is not proven. Not human commissioned.

## BEFORE

Packs 1–4 were already committed locally (SQLite, sessions, RBAC, bug/UX). Those reports were engineering checks, not a commissioned hotel ledger.

On an empty database the app still did four things that read as hotel history:

- It posted two OPERA night-audit journals (August and September 2026) with large room-revenue figures.
- It loaded sample inventory quantities, suppliers, and storeroom managers.
- It loaded sample service-charge staff, bank accounts, and collections.
- It could generate 98 apartment owners with bank details. `data/atrium.sqlite` already held that generated register (98 units, first owner `Ir. Hendra Gunawan`) plus 98 owner-email dispatch rows. `data/owner_pool.json` and `data/owner_email_store.json` are the same sample, and they are tracked in git.

The command centre showed those figures in dollars. Property settings started as 120 rooms and a period lock of 2026-07-31. The sixth role (auditor) had no sign-in. Saving hotel settings did not write them to SQLite. A Google button on the login screen does not open a server session. Service charge had a button that reloaded the sample staff.

No `.env` file was present. `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, and `B2_ENDPOINT` were empty in the environment.

## BUILT-REPAIRED

- Empty books stay empty. Startup no longer writes night-audit journals, stock, staff, or owners.
- The command centre says the property profile is not set and that there are no posted journals. Amounts use IDR. A zero is not shown as a dollar total when nothing has been posted.
- Property profile starts blank: no name, room count 0, no period lock. Saving settings now persists. Mapping is marked confirmed only when all four counterpart accounts are filled in.
- Tax types are present as a list. Rates are 0 and `is_rate_configured` is false until a controller enters them.
- The service-charge sample button is gone. `POST /api/service-charge/seed-defaults` returns 409 and does not write staff.
- PMS night-audit boxes start empty. Submitting them blank is refused.
- Revenue and spending previews say "Not entered" and use Rp.
- Empty lists for receivables, payables, inventory, employees, and units say that nothing has been entered.
- Six role logins exist, named by role, not by a person: Financial Controller, General Accountant, Front Office / Night Auditor, Accounts Payable & Purchasing Clerk, General Manager / Hotel Owner, Internal & External Auditor. Addresses are `*@seed.invalid` until a controller replaces them. Passwords come from `SEED_*_PASSWORD` or a random hash with no recorded plaintext. The known fallback `AtriumHotel2026!` is gone from the working tree.
- Login labels are tied to the fields. The Google button is not on the sign-in screen.
- The server finishes loading SQLite before it listens.
- `data/atrium.sqlite` (the 98-unit sample) was moved to `data/uncommissioned/`, which is gitignored. It was not deleted. A normal boot no longer opens it.

The USALI chart of accounts is still created on an empty database. That is a chart template, not posted hotel history.

## VERIFIED

Production and beta were still the original processes after the proof:

```
Python 15975 127.0.0.1:8787
Python 47662 127.0.0.1:8788
```

`npx tsc --noEmit --pretty false` exited 0 with no diagnostics.

`npm test` (`node --import tsx --test --test-concurrency=1 tests/*.test.ts`):

```
ℹ tests 10
ℹ pass 10
ℹ fail 0
ℹ skipped 0
ℹ duration_ms 4006.243084
```

Live server: `PORT=8790`, `DATABASE_FILE=/tmp/atrium-sprint7-20260927/app.sqlite`, `SESSION_SECRET` and six `SEED_*_PASSWORD` values set only in that process. Passwords are not recorded here.

Unauthenticated calls, 135 `/api` routes enumerated from `server.ts` and `server/auth.ts`:

```
401: 132
public GET /api/health: 200
public POST /api/auth/logout: 200
public POST /api/auth/login with {}: 400
unauthNon401: []
```

Six logins returned 200. Each cookie was `HttpOnly` and `SameSite=Lax`. Response bodies had no `password` field. Role ids were the six `role-*` ids, not person names.

Cross-role calls on the running server, all matched the expected status: front office dashboard 200 and settings/journals/accounts 403; purchasing inventory 200, financial statements 403, journal post 403; general manager journals 200, access-control 403, revenue post 403; auditor journals and tax rules 200, revenue post and journal delete 403; accountant settings 403 and journals 200; controller settings, units, employees, items, AR, and AP 200; sample staff endpoint 409.

Empty reads on that database before the persistence probe: revenue 0, units 0, employees 0, inventory items 0, tax rules 9 with 0 rates configured, property name blank, room count 0, period lock blank, posted journals in the period 0, currency IDR.

Persistence: accountant `POST /api/revenue` created `REV-TX-MUIQRMXS-984` for amount 1 with description `scratch persistence probe` (scratch database only). The proof process was killed. The same database was opened again on `:8790`. Login and `GET /api/revenue` returned that row. `POST /api/auth/logout` then the same cookie on `/api/revenue` and `/api/auth/me` returned 401.

SQLite `users.password` for all 6 rows started with `$2` and length 60. Plaintext rows: 0.

Headless Chrome (system Google Chrome via playwright-core, not added to the app dependencies) at 1280×900 and 390×844: empty login blocked, bad password showed an error, dashboard empty wording, reload kept the session, operations/AR, spending/AP, inventory, service charge, owner pool, tax, configuration, controls, integrations, and administration opened, property profile starts blank, logout returned to the login screen and stayed there after reload, and each of the other five roles was blocked from a pillar their role cannot view. Desktop overflow 1280/1280. Phone overflow 390/390. Page errors: none. Issue count: 0.

Git: no `.env` or `*.sqlite` filename in history. `.env.example` is the only env file tracked. `BEGIN PRIVATE KEY` appears only as a sentence in `docs/wolf/PACK3-REPORT.md` saying it is not in source. Older commits `54ac7de` and `dd090d1` still contain the retired password literal in `server/store.ts`. The working tree does not. History was not rewritten.

B2: the four variables were absent. No upload and no restore. `tests/backup.test.ts` still passes for the local checkpoint copy and for the "missing credentials do not count as a backup" case.

## STAFF READY?

YES for the ledger, on a fresh database, for a person to start commissioning by role.

NO for offsite backup. NO for the quarantined sample file or the tracked `data/owner_pool.json` / `data/owner_email_store.json`. Those are not the hotel register.

## HUMAN COMMISSIONED?

NO

## BLOCKERS

- BLOCKER: B2 credentials needed. No application key was in the environment or in `.env`. Upload and restore were not run.
- The tracked JSON files under `data/` are the old generated owner sample. Do not run `scripts/migrate-json-to-sqlite.ts` on them unless a human has confirmed every row.
- `data/uncommissioned/atrium.sqlite` is that same sample (98 units, 98 email rows). Do not point `DATABASE_FILE` at it.
- Seed addresses are `*@seed.invalid`. A controller must replace them with real role mailboxes and set passwords in the environment before first boot. Those passwords are not in git.
- Older git commits still contain the retired password literal. The current tree does not. History was not rewritten.
- Tax rates, the property profile, opening balances, staff, stock, and owners are empty on purpose. A human has to enter them.

## NEXT HUMAN TEST

1. Stop anything on `:8790` if it is still the scratch proof.
2. Choose a new database file that is not `data/uncommissioned/atrium.sqlite`.
3. Set `SESSION_SECRET` and the six `SEED_*_PASSWORD` values in the environment. Do not commit them.
4. Start with `PORT=8790 npm run dev`.
5. Financial Controller signs in at `controller@seed.invalid`, opens Administration → Period Closing Locks & Hotel Master Profile, and saves the real property name, room count, and currency. Leave the period lock empty until a period is actually closed.
6. Confirm Command Centre says there are no posted journals.
7. Each of the other five roles signs in and confirms a locked pillar shows "does not have viewing permissions".
8. Enter one real draft only when the figures are from the hotel. Do not type a sample.

## FOUNDER DEPENDENCY

- Sign-in and role checks: ELIMINATE. The gate uses `roleId`. Seed names are role titles.
- Sample night audit, sample stock, sample staff, sample owners, and the Google button: ELIMINATE. They no longer run.
- Night-audit form: AUGMENT. Front Office types the hotel's figures into empty boxes.
- Property profile, tax rates, chart confirmation, opening balances, real staff, real stock, real owners: RETAIN for the Financial Controller role (and the roles that are allowed to enter drafts). This does not add a new dependency on Matt.
- Offsite backup: RETAIN until a human supplies a scoped B2 key. Do not invent one.

RESULT: PASS
