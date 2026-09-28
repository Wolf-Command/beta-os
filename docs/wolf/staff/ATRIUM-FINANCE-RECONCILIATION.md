# ATRIUMFIN-RECON-1 — Atrium Finance reconciliation

Discovery only. No product was built. No server was started. Production `:8787` was not contacted. `~/atrium-finance` and `~/.openclaw` were read only. The screenshot Zayen supplied on 28 Sep 2026 is not on disk, so the module list is taken from code. Pixels in that screenshot are unconfirmed.

Checked 28 Sep 2026.

| Source | What it is | Where |
| --- | --- | --- |
| A | Beta desk Zayen reached | `dashboards/amg-finance.html`, `scripts/core/atrium_finance_desk.py`, `scripts/core/atrium_books.py`, `scripts/core/staff_access.py`, `scripts/serve_beta.py`, `state/atrium-books/amg.sqlite` |
| B | The app in his GitHub repo | `/Users/wolfterminal/atrium-finance`, origin `https://github.com/Zaynn28/ATRIUM-FINANCE` |
| C | Production Wolf desk | `~/.openclaw/workspace/wolf-system/dashboards/atrium-finance.html` (3120 lines on disk), `dashboards/assets/finance-desk.js`, `dashboards/serve.py`, `atrium-finance/atrium_finance.sqlite` |
| D | Wolf finance core in this repo | `docs/wolf/finance/BZG-FINANCE-REUSE-PLAN.md`, `scripts/core/fin_*.py`, `scripts/core/atrium_books.py` |
| E | Auth already done | Cloudflare Access plus Wolf person, role, assignment, scope, permission. Role Atrium Finance Officer |
| F | Backup already sketched | `scripts/backup-to-b2.ts` in B. Offsite job is not loaded |
| G | Intended modules | Navigation in B `src/App.tsx` and `src/components/Navbar.tsx`, plus the rail in C |

## 1. Root cause

Beta `/amg/finance` is a reduced desk because that is the page this repo built for the seat. The full product was never wired into Beta.

There are two fuller implementations, and neither is what `serve_beta.py` serves:

- B is the TypeScript application he pointed at (Vite, React, Express, SQLite). It is not imported by Beta.
- C is the production HTML desk on the Wolf tree (Python, `atrium_finance.sqlite`). Beta has no copy of `atrium-finance.html`. A search of this repo's history shows `amg-finance.html` only. The first commit of that file is the placeholder replacement `601b522`.

What Beta did, in order:

1. Owner brief 28 Sep 2026 11:28 WITA, staff access (`docs/wolf/staff/STAFF-ACCESS-RESULT.md`). That pack created `ROLE-AMG-FINANCE-OFFICER` for `PERS-ZAYEN`, scope `ENT-AMG` only, and copied a subset of read and draft routes from B `server/routeAccess.ts`. It did not open the books. The page at that point was the engineering placeholder.
2. Zayen reached that placeholder (human FAIL #2, 14:16). The sentences on it were "Hotel books are not open on this desk.", "No report figure is on this page.", "Do not type an amount.", and "You cannot approve a payment…".
3. ATRIUMFIN-UX-1 (`601b522`) replaced the placeholder with Board and Approvals.
4. ATRIUMFIN-UX-2 (`d528c3c`) added Ledger, Chart of Accounts, draft journals, and statement names.
5. ATRIUMFIN-UX-3 (`d9029f6`, 28 Sep 2026 15:19 +0800) is the desk he retested. Head of this repo at the time of the retest.

`scripts/core/atrium_finance_desk.py` states the cut in code. `WITHHELD` is commented "Built in production, left off this desk because the seat cannot do them safely." The withheld ids are cash, configuration, night audit, procurement, payment run, payroll, journal approve, and journal post. `ATRIUM_DENIED` and `ATRIUM_HELD_BACK` in `scripts/core/staff_access.py` are the same cut on the grant list. UX-1, UX-2, and UX-3 each say they added no grant.

`scripts/core/atrium_books.py` copied the Atrium chart from production and left the journals behind: "No production journal, balance, bank row, or payment is copied."

RETEST #2 is a routing pass and a product fail for that reason. Routing to `/amg/finance` works. The page is the reduced desk, not B and not C.

## 2. Where the full implementation lives

### B — the repo he named

| Item | Value |
| --- | --- |
| Clone | `/Users/wolfterminal/atrium-finance` |
| Origin | `https://github.com/Zaynn28/ATRIUM-FINANCE` |
| Current branch | `wolf/foundation-20260926` |
| Tip | `37a0ff9378d9c23891b1e7dd0397065445e81b5d` (27 Sep 2026 07:51 +0800), "Stop prefilling a new-user password and add a fresh-database start script." |
| Working tree | Clean |
| Upstream | None. The branch is local only |
| `origin/main` | `9f854bffc449840bbd74b7584457e3b0fbdf03cd` (25 Sep 2026 10:27 +0800), "feat: add owner distribution email automation." |
| Divergence | Tip is 6 commits ahead of `origin/main` and 0 behind. Those 6 commits are SQLite persistence, session login, RBAC, the B2 script, stopping the sample hotel history, and the fresh-database start script |

Local branches: `main` (same commit as `origin/main`) and `wolf/foundation-20260926`. Remote branches: `origin/main` only.

Layout: `server.ts`, `server/`, `src/`, `data/`, `scripts/`, `tests/`. Persistence is SQLite through `better-sqlite3` (`server/db.ts`, default file `data/atrium.sqlite`). `src/services/firebase.ts` still constructs Firebase Auth and Firestore. No other file under `src/` or `server/` imports it. The sign-in screen does not use Google. Pack 4 removed the Sheets badge and the sheets diagnostic routes. `server/sheets.ts` remains as an optional mirror and the UI does not call it.

`server.ts` listens on `0.0.0.0` and port `process.env.PORT` or 3000. This recon did not start it.

This session, in that clone, with no `.env` file present: `npx tsc --noEmit --pretty false` exited 0 and printed nothing. `npm test` was not run. The tests bind `127.0.0.1`. The last written test result is `docs/wolf/sprint7/P2-FINANCE-RESULT.md` (27 Sep 2026, same branch): 10 pass, 0 fail, on a scratch database that was then stopped. That run is not repeated here.

A fresh boot path is `scripts/start-fresh-commissioning.sh`. The commissioning note says it refuses ports 8787 and 8788 and refuses `data/uncommissioned/`. It was not started.

### C — production Wolf desk

| Item | Value |
| --- | --- |
| Tree | `~/.openclaw/workspace/wolf-system` |
| Branch | `live/mac-studio-gates` |
| Committed HEAD | `7c5564a` (11 Sep 2026 13:50 +0800), "fix: Atrium payroll banner truth (PR #144 surgical soft-apply)" |
| HTML on disk | 3120 lines. `git show HEAD:dashboards/atrium-finance.html` is 2460 lines. The file is modified and uncommitted |
| Also dirty | `dashboards/assets/finance-desk.js`, `dashboards/atrium_finance.py`, `dashboards/serve.py` (diffstat 1386 insertions, 32 deletions across those four files) |
| Books | `atrium-finance/atrium_finance.sqlite` |
| API | `serve.py` `_accounting_authorized` at line 1994. GET and POST `/api/accounting` call `atrium_finance.handle`. GET and POST `/api/atrium-finance` use the `atrium_finance_allow` list. `finance-desk.js` calls those paths |

GitHub pulls 146 through 164 (`wolfcommand/wolf-system`) all have an empty `mergedAt`. None of them is a merge onto `live/mac-studio-gates`. Atrium-related titles:

| PR | State | Title |
| --- | --- | --- |
| 146 | CLOSED | Accounting Core ALWAYS-band and draft delete |
| 149 | CLOSED | PSAK and USALI reports from posted journals |
| 150 | CLOSED | PSAK and USALI as their own ALWAYS-band section |
| 152 | OPEN | Phase 1 top nav shell |
| 154 | OPEN | Operations area shell |
| 156 | OPEN | Surgical add of the operations shell |
| 158 | OPEN | Command Centre read and monitor only |
| 159 | OPEN | Configuration home, chart editor |
| 160 | OPEN | Unique journal number for manual journals |
| 164 | OPEN | Zayen cannot click Atrium Finance area tabs |

The other numbers in 146–164 are GGV invoice, nota, invite, or Sterling brand wires (147, 148, 151, 153, 155, 157, 161, 162, 163). They are not the Atrium product. Because the live HTML is dirty against HEAD, some of the open PR work may already be sitting uncommitted on the Mac. This recon did not stage, commit, or check that tree out.

Production `:8787` was not probed.

## 3. Module table

Status is about Beta `/amg/finance` at `d9029f6`. "Working" means the reduced desk does the small job it was given. It does not mean the full module is present.

The screenshot is not on disk. Rows come from B's nine pillars and from C's rail. Where a C label has no B pillar, the row says so.

| Module | Status on Beta | Source |
| --- | --- | --- |
| Board (Beta only) | PRESENT AND WORKING. Empty. `consolidation_figure` is null. Copy says the books are not open yet, so there is no balance. | `dashboards/amg-finance.html` `#board`. `atrium_finance_desk.py` `BOARD_EMPTY`. `GET /amg/finance` |
| Command Centre | EXISTS ELSEWHERE. This is B's home and C's `data-go="control"`. Beta Board is not that screen. | B `src/components/DashboardView.tsx`. C rail "Command centre" |
| Ledger | PRESENT AND WORKING as an empty general ledger. `journal_line` count in the Beta books file is 0. | `GET /amg/finance/ledger`. `atrium_books.py` `LEDGER_EMPTY` |
| General ledger (full) | EXISTS ELSEWHERE. | B `src/components/GeneralLedgerView.tsx`. C Accounting Core |
| Chart of Accounts, names only | PRESENT AND WORKING. 190 rows, no balance column. First code in the UX-3 shot is 1000 Cash and Equivalents. | `GET /amg/finance/accounts`. Seed `scripts/core/data/atrium_coa_seed.json` (`source` field: production `coa_account` where `entity_id=ent-atrium`) |
| Chart editor, departments, mapping, report designer | EXISTS ELSEWHERE. `finance.policy.admin` is in `ATRIUM_DENIED`, and configuration is in `WITHHELD`. | B `src/components/ConfigurationView.tsx`, `ChartOfAccountsView.tsx`, `MappingModal.tsx`, `configuration/ReportConfigDesigner.tsx`. C `data-go="master"`. PR 159 is open |
| Journals, balanced draft | PRESENT AND WORKING. Save stays a draft. The live Beta books file has 0 drafts. The UX-3 saved-draft shot used a temp file. | `GET/POST /amg/finance/journals`. `atrium_books.py` `journal_draft` |
| Journal validate, approve, post, reverse, delete | PRESENT BUT NOT WIRED for this seat. Approve and post are registered and return 403. They stay in `ATRIUM_HELD_BACK`. The workbench UI is not on the page. | B `JournalWorkbenchView.tsx` and `server/routeAccess.ts` journal rows. C `finance-desk.js` posts to `/api/accounting/journals` |
| Trial balance | EXISTS ELSEWHERE. No Beta route. | B `TrialBalanceView.tsx`. C Accounting Core subtitle |
| Reports, five names, no figures | PRESENT AND WORKING as a name list. Families PSAK and USALI: profit or loss, statement of financial position, USALI operating statement, USALI balance sheet, USALI rooms schedule. | `report_definition` in `state/atrium-books/amg.sqlite`. `GET /amg/finance/reports` |
| USALI and financial drill-down | EXISTS ELSEWHERE. | B `src/components/reports/`. C PR 149 and 150 (closed, not merged) |
| Approvals, describe and send | PRESENT AND WORKING. Her own Atrium requests. The form has no amount. She cannot decide. The page says approvals are handled by the Finance Controller. | `GET/POST /api/amg/finance/approvals`. `ATRIUM_SUBMIT` is `approval.request`. `approval.decide` is denied |
| Revenue cycle and accounts receivable | EXISTS ELSEWHERE. | B `RevenueCycleView.tsx`, `src/components/ar/AccountsReceivableModule.tsx` |
| Spending cycle, procurement, accounts payable | EXISTS ELSEWHERE. Payment is withheld on the seat. | B `SpendingCycleView.tsx`, `src/components/ap/AccountsPayableModule.tsx`. C `data-go="procure"` |
| Inventory (overview, item master, categories, storerooms, requisitions, purchase orders, receiving, issue, transfer, count, adjustment, stock card, cost reports, barcode) | EXISTS ELSEWHERE. | B `src/components/inventory/InventoryModule.tsx` |
| Service charge | EXISTS ELSEWHERE. The sample-staff button is off (`POST /api/service-charge/seed-defaults` returns 409 in the 27 Sep note). | B `src/components/operations/service-charge/`. C `data-go="payroll"` |
| Owner pool, statements, email distribution | EXISTS ELSEWHERE. Real owner register is not in the fresh database. The 98-unit file is sample. See section 4. | B `src/components/operations/owner-pool/`. C `data-go="owner"` |
| Tax | EXISTS ELSEWHERE. On a fresh B database the 27 Sep note says the names exist and the rates are not set. | B `src/components/TaxModule.tsx`. C `data-go="tax"` |
| Controls and audit | EXISTS ELSEWHERE. | B `ControlsAuditView.tsx`. C master-data rail mentions the log |
| Integrations, PMS night audit | EXISTS ELSEWHERE. BLOCKED BY REAL DATA/INTEGRATION. No commissioned PMS feed was found. C has 28 `night_audit_run` rows, all `PENDING`, and `revenue_daily` count 0. | B `IntegrationsView.tsx`. C `data-go="nightaudit"` |
| Administration, users, period lock, property profile | EXISTS ELSEWHERE. B's own user table and persona switcher conflict with Wolf auth. See section 5. | B `AdministrationView.tsx`, `administration/UserAccessManager.tsx`. C administration is not a Beta route |
| Cash and bank | EXISTS ELSEWHERE. In `WITHHELD`. C `bank_account` count is 0. | C `data-go="cash"`. No B pillar with this name. Bank position is not a Beta page |
| Payment run | EXISTS ELSEWHERE. `payment.execute` is denied. C `payment_run` count is 0. | C `data-go="payrun"` |
| Month-end close | EXISTS ELSEWHERE. C `close_checklist_item` count is 12. Whether those 12 rows are a template or a live close was not opened row by row. | C `data-go="close"`. B administration period lock is the nearest B surface |
| Pre-opening and assets | EXISTS ELSEWHERE. C `asset` count is 0. `asset_category` count is 6. | C `data-go="assets"` |
| GM morning flash | EXISTS ELSEWHERE. No matching B pillar name. | C `data-go="flash"` |
| Handoff | EXISTS ELSEWHERE. C only, from the rail. Not confirmed against the missing screenshot. | C `data-go="handoff"` |

C's operations buttons (night audit, flash, procurement, cash, payroll, tax, close, owner, assets) match the rail. They are the production desk's day rhythm, not extra Beta tabs.

## 4. Data truth

Do not copy any sample figure onto the Beta desk.

### Sample or template

| Item | Evidence |
| --- | --- |
| Old hotel history inside B | Commit `b4f800e` (27 Sep 2026 02:54 +0800): "Stop empty books from loading sample hotel history." `seedInitialPostedNightAuditRevenueIfEmpty` is now an empty function. The 27 Sep P2 note says a previous boot posted two OPERA night-audit journals, sample stock, sample service-charge staff, and could generate 98 owners |
| Uncommissioned SQLite | `data/uncommissioned/README.txt`: moved off the default path on 27 Sep 2026. Counts read here: `owner_pool_units` 98, `owner_email_dispatches` 98, `accounts` 0, `journal_headers` 0. The readme says this is the old sample seeder, not a commissioned register |
| Tracked JSON | `data/owner_pool.json` and `data/owner_email_store.json` are the same sample family. P2 says do not import them |
| USALI chart created on an empty B database | Template accounts in `server/store.ts` `seedStandardHotelAccounts`. A chart is not last month's books |
| Seed sign-in | Six roles, addresses `*@seed.invalid` unless the environment overrides them. Passwords are environment or a random hash. The shared fallback password was removed on this branch |
| Tax rates on a fresh B database | P2: 9 tax rules, 0 rates configured, until a controller types a rate |
| Beta statement page | Five names. No posted period, so no figures. `atrium_books.py` `REPORT_EMPTY` |
| Beta journal form in the UX-3 screenshot | The 150000 / 150000 lines were typed into a temp books file for the shot. `state/atrium-books/amg.sqlite` was not that file |

### Production SQLite

File: `~/.openclaw/workspace/wolf-system/atrium-finance/atrium_finance.sqlite`. Read only.

Posted journals: 18. Header debit equals header credit on all 18. Line debit equals line credit on all 18. Source module `ACCOUNTING_CORE`. Business date on all of them is 2026-09-01. Posted-at runs from 2026-09-01T13:31:33+0800 to 2026-09-09T13:31:12+0800. `created_by` on all 18 is `zayen@atriumlombok.com`.

They are not a hotel trading history. `journal_type` is `TEST` on 12 and `REVERSAL` on 6. Description prefixes group as `TEST CORE 2026-09-01` (12) and `REVERSAL of JE-202609-00` (6). Sum of `total_debit` on `POSTED` rows is 18000000. That sum is the test set. It is not a balance to put on the Board.

Other journal statuses, all header-balanced: `DRAFT` 38 (37 by the same created_by, 1 by `test`), `VALIDATED` 5, `APPROVED` 2, `REJECTED` 1.

Periods: `2026-09` is `OPEN` on `ent-01`, `ent-atrium`, and `ent-ggv`. `2026-08` and `2026-10` are `OPEN` on `ent-01`. Nothing in that table is `CLOSED`.

Chart: `ent-atrium` 190 accounts (170 postable). `ent-ggv` 55. The Beta seed is the 190 Atrium rows, names and classes only.

Empty operational tables include `revenue_daily` 0, `folio` 0, `ap_invoice` 0, `ar_invoice` 0, `vendor` 0, `bank_account` 0, `payment_run` 0, `purchase_order` 0, `employee` 0, `service_charge_pool` 0. `night_audit_run` is 28, every row `PENDING`. `pms_import_batch` is 28. Entity rows `ent-01`, `ent-02`, and `ent-03` are `created_by` `seed`. `ent-atrium` is `created_by` `seed`. `ent-ggv` is `created_by` `ggv-seed`.

### Beta books file

`state/atrium-books/amg.sqlite`. sha256 `334cfa3541ce8ae597d0bd07e6c89b87cf4d67867c37bda685c47ef0923f2a64`. That is the same hash recorded in the UX-3 note. This recon did not write it.

Counts: `coa_account` 190, `journal_draft` 0, `journal_line` 0, `report_definition` 5.

## 5. Security that stays

Keep all of this on the Beta path:

- Cloudflare Access in front of Beta. Live mode is `cloudflare_access`. A spoofed `X-Wolf-Subject` does not sign her in.
- Wolf chain: person `PERS-ZAYEN`, role `ROLE-AMG-FINANCE-OFFICER` (label Atrium Finance Officer), position `POS-AMG-FINANCE-OFFICER-1`, assignment `ASG-ZAYEN-FIN-1`, scope `ENT-AMG` only.
- Grants she has: `atrium.board.read`, `atrium.ledger.read`, `atrium.journal.draft`, `atrium.report.read`, `atrium.coa.read`, and `approval.request`.
- Held back: `atrium.journal.approve`, `atrium.journal.post`.
- Denied, among others: `payment.approve`, `payment.execute`, `vendor.bank.change`, `approval.decide`, `finance.policy.admin`, `organisation.role.read`, `core.operator`, GGV nota, hotel day, content, progress.
- The Atrium wall in `serve_beta.py` (`_atrium_finance_wall`) so this seat does not open GGV, Blu Zone, or Owner.
- Audit and evidence on the Wolf side. Production `audit_log` has 631 rows. That table stays in the production file. It was not copied.
- Backup and restore as a requirement, not as a claim that it already runs. B has `scripts/backup-to-b2.ts` and `scripts/com.atriumfinance.backup.plist` (03:00). Pack 4: local copy is built, upload was not tested, the plist was not loaded, and a restore drill was not done. The 27 Sep commissioning note: no `.env`, the four B2 variables unset, plist not loaded. A separate scratch upload that day went to `b2:wolf-cold-archive/atrium-finance-d5-scratch/` and is marked a test object, not the hotel books.
- Least privilege for this seat. General Accountant in B can draft and cannot approve, change administration, or delete. The Wolf grants are that shape. They are not Financial Controller.

### Conflicts with B's own login

B gates `/api` with a hashed password and an httpOnly session cookie (`server/auth.ts`, commits `dd090d1` and `c28a122`). It seeds six role users and an administration screen that can switch the active user. The navbar still has a "Switch Role Persona (Simulator)" menu. That is a second user store and a second session, beside Cloudflare and Wolf RBAC.

`src/services/firebase.ts` still initialises Firebase Auth and Firestore from `firebase-applet-config.json`. Nothing else imports that module, and the Google button is gone from the sign-in screen. If the Vite bundle ever imports it, Beta would grow a third identity. The file should stay out of the Beta bundle.

Production `serve.py` is a fourth door: `_accounting_authorized` allows an identity on the entity allow-list, and a request that is not via Cloudflare and has no Access identity is treated as local. That is not the Beta Wolf role check.

Three addresses already exist for one human: `laluzayen@gmail.com` on the Wolf seat, `zayen@atriumlombok.com` as `created_by` on the production test journals, and `accountant@seed.invalid` as the B General Accountant seed. One Wolf identity has to be the only sign-in.

Owner-pool email send (`/api/owner-pool/email-drafts/:id/send` and email-all) is a mail path on B's reports permission. It does not belong on this seat, and it must not point at the sample dispatch rows.

## 6. Shortest safe path

One product. Beta `/amg/finance` becomes the full Atrium Finance surface. Wolf finance core remains the books, the audit, and the evidence. Wolf auth remains the only login. B's Express process does not become a second server. C's HTML file is not copied in as a second page.

### Options

| Option | Effort | Risk | What it does |
| --- | --- | --- | --- |
| 1. Grow the Beta desk, pillar by pillar, using B as the module spec and Wolf APIs as the only backend | Large. The first slice (Command Centre empty-honest, ledger, chart, drafts, statement names, trial balance read) is the smaller part. Inventory, tax calculation, owner pool, night audit, cash, and pay are further slices | The seat can be kept inside the grants that already exist. A money path has to be added on purpose, in a later pack, for a controller seat that does not exist yet | This is the path that keeps one runtime |
| 2. Mount B's React UI inside Beta and delete its session, its user table, and its persona switcher, so the screens call Wolf routes | Large, similar to option 1, with a front-end port on top. Typecheck already passes on `37a0ff9` | `server.ts` binds `0.0.0.0`. Any shortcut that runs that process beside Beta recreates the second login. Firebase initialisation has to stay unimported | Same destination as option 1 if the Express server is not run |
| 3. Reverse-proxy or iframe B on a private port behind Cloudflare | Short | Second product. Second session. Sample boot if `DATABASE_FILE` points at `data/uncommissioned/` or the tracked JSON. Owner email can send. This fails the "one product" rule | Rejected |
| 4. Serve C's `atrium-finance.html` from Beta | Medium, and the file is dirty against `7c5564a` | That page talks to `/api/accounting` and the allow-list, not Wolf RBAC. The 18 posted rows are `TEST` and `REVERSAL`. A board that sums them would show a test figure as the hotel position. PR 164 is still open because the area tabs already fail for this person on that page | Rejected as the Beta product |

### Recommendation

Option 1. Use B `wolf/foundation-20260926` at `37a0ff9` as the module list. Keep serving from Beta. Keep the grants in `staff_access.py`.

Order:

1. Leave `ATRIUM_DENIED`, `ATRIUM_HELD_BACK`, and `WITHHELD` as they are until a Finance Controller seat is a separate decision.
2. Bring the read surfaces the seat can already hold: Command Centre that states the property is unset and that no operational journal is posted, trial balance with no rows, and the report names already on the desk. Figures stay absent while the only posted production journals are the `TEST` and `REVERSAL` set.
3. Keep draft journals on `state/atrium-books/amg.sqlite` until a controller posts. Do not import production `journal_header`.
4. Leave cash, payment run, bank change, night-audit posting, payroll, owner email, administration, and the persona switcher off the seat.
5. Treat PMS, bank, payroll, and a real owner register as blocked until those feeds exist. Empty stays empty.
6. Point backup at the Beta books file only after the B2 key is a scoped write key and a restore drill is written down. The scratch object from 27 Sep is not that backup.
7. Production `:8787` stays on its current process until a later cutover decision. This recon does not make that decision.

`staff_ready` and `human_commissioned` stay false. RETEST #2 stays a product fail until the desk is the product in section 3 and a human writes PASS.

RESULT: PASS
