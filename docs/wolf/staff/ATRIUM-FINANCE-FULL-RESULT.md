# ATRIUMFIN-FULL-1 — Full Atrium Finance product on Beta

Decision served: Matt, 28 Sep 2026 16:31 WITA. Zayen's product, as specified since last week, is the Atrium Finance product. Once it is working it is the framework for BZG and GGV finance. `staff_ready` and `human_commissioned` stay false.

## What is mounted

One product, one login. Beta `:8788` stays the Wolf door. After Cloudflare Access, `_atrium_finance_wall`, and the existing Atrium RBAC check, `scripts/serve_beta.py` reverse-proxies `/amg/finance` and `/amg/finance/*` to the sidecar. `/amg/finance/lite` and `/api/amg/finance` stay on the reduced desk and are not proxied.

The sidecar is Zayen's server from `~/atrium-finance`, branch `wolf/beta-mount-20260928`, commit `7ec34a5`, off `37a0ff9`. It listens on `127.0.0.1:8790` only. Vite base is `/amg/finance/`. Browser API calls go to `/amg/finance/api`, and the sidecar rewrites that prefix back to `/api` before his route table. His password login, the role-persona simulator, and administration user-switch are hidden when `VITE_BETA_MOUNT=1`. `POST /api/auth/login` and `POST /api/admin/access-control/switch-user` return 403 in this mode.

`src/services/firebase.ts` is still in his tree. No other source file imports it. A production Vite build (`VITE_BASE=/amg/finance/`, `VITE_BETA_MOUNT=1`) wrote `dist/assets/index-DbSNQIhL.js` with no `firebase` string. The live sidecar is `tsx server.ts`, the same source, not `dist/server.cjs`.

The reduced desk code is kept. `/amg/finance/lite` serves it, with its links rewritten to the lite prefix.

Entity slots live in `server/entityConfig.ts`. `ENT-AMG` is enabled. `ENT-GGV` and `ENT-BZG` are reserved with `enabled: false`. They are not built in this mount. Zayen still receives 403 on `/ggv/finance`, `/bzg/uma-blu`, and `/api/ggv/finance/pay`.

Beta commit for the proxy, launcher, tests, and screenshots: `47536c2` on `build/wolf-command-rebuild`. Neither commit was pushed. His GitHub remote was not updated.

## Listeners after that commit

Started with `state/build-factory/detach.py`.

| Process | Pid | Parent | Started | Bind |
| --- | --- | --- | --- | --- |
| Sidecar launcher (`npm exec tsx server.ts`) | 96397 | 1 | Mon Sep 28 17:36:58 2026 | |
| Sidecar listener | 96416 | 96415 | Mon Sep 28 17:36:58 2026 | `127.0.0.1:8790` |
| Beta `scripts/serve_beta.py` | 96450 | 1 | Mon Sep 28 17:37:09 2026 | `127.0.0.1:8788` |
| Production `serve.py` | 15975 | | Mon Sep 21 16:59:38 2026 | `:8787` unchanged |

Live `:8788` auth mode was left as it was. `GET /api/health` on `:8788` is 200. Unsigned `GET /amg/finance` on `:8788` is 403. Sidecar `GET /api/health` is 200. Unsigned sidecar `GET /amg/finance/api/journals` is 403. A signed Zayen assertion on the post-commit sidecar returns dashboard 200 (`propertyConfigured` false, every posted figure 0, `propertyName` empty) and journals `[]`. Approve and admin return 403 with `money_movement` false.

## Role map

Wolf remains the only sign-in. Beta strips client identity headers, then sets `X-Wolf-Assertion`: HMAC-SHA256 over canonical JSON, 60-second expiry, bound to method and path. The sidecar accepts that header only from loopback (`127.0.0.1`, `::1`, `::ffff:127.0.0.1`) and only when the signature matches. Audit rows in `wolf_audit` store the Wolf person id.

| Wolf | His role | What that seat can do here |
| --- | --- | --- |
| `ROLE-AMG-FINANCE-OFFICER` and `PERS-ZAYEN` (`laluzayen@gmail.com`) | `role-general-accountant` | Drafts and ledger reads. `configuration.canView` is on so the chart can be read. Create, edit, approve, delete, and export on configuration stay off. |
| `ROLE-OWNER` and `PERS-MATT` | `role-general-manager-owner` | Read. |
| Anyone else | no seat | 403 |

No Financial Controller user is created. `usr-controller-1` is absent. That seat is a later Matt decision.

`ATRIUM_DENIED` and `ATRIUM_HELD_BACK` were not edited. His server also refuses, for both mapped seats, any `/api/admin` path, any path containing `/bank`, and `POST`/`PUT`/`PATCH`/`DELETE` of journal approve, post, reverse, `/api/ap/payments`, `/api/tax/payment`, owner-pool email send, and `/api/auth/login`.

## Security proof

His checklist, re-run on `7ec34a5` before the listener restart: `npx tsc --noEmit` exit 0. `npm test` 14 pass, 0 fail. That run includes password hashes and the login rate limit, SQLite boot, a permission rule on every API route, helmet, same-origin CORS, and validation. The new tests cover the assertion round trip, the role map, the sensitive matcher, and loopback.

Beta `scripts/tests/test_atrium_full_mount_20260928.py`: `SUMMARY pass=79 fail=0`. Unsigned 403 on `/amg/finance`, its API, and `/amg/finance/lite`. A forged assertion is 403. A client-supplied identity header is ignored. Zayen receives 200 on the read pages and 403 on approve, post, pay, tax payment, bank, admin, switch-user, and login, both on the sidecar and through a signed Beta test handler. The sidecar refuses `192.168.77.75:8790` and `100.113.26.51:8790`. `lsof` shows `127.0.0.1:8790` and not `*:8790`.

Suites that had to stay at fail 0, re-run with the sidecar up:

| Suite | Result |
| --- | --- |
| `test_atrium_finance_ux_20260928.py` | pass=212 fail=0 |
| `test_staff_access_20260928.py` | pass=274 fail=0 |
| `test_role_routing_20260928.py` | pass=84 fail=0 |
| `test_zarah_frail_cd_20260928.py` | pass=150 fail=0 |
| `test_ggv_finance_invoice_20260928.py` | PASS=92 FAIL=0 |
| `test_ggv_finance_mobile_nota.py` | PASS=138 FAIL=0 |
| `test_ggv_finance_nota_storage_accountant.py` | PASS=100 FAIL=0 |

Screenshots from the signed test handler, headless Chrome, desktop 1440 and phone 390: `docs/wolf/staff/shots/atrium-full-{command,journal,ledger,trial,reports,inventory,ar,ap}-{desktop,phone}.png`. The live `:8788` auth mode was not switched to take them.

Secrets are `~/atrium-finance/data/beta/secrets.env`, mode 600, gitignored. They were not printed and not committed. The launcher `scripts/serve_atrium_finance.sh` creates that file when it is missing and does not echo it.

## Data truth

Database: `~/atrium-finance/data/beta/atrium.sqlite`. `data/uncommissioned/` was not used. `owner_pool.json` and `owner_email_store.json` were not imported. No sample seed.

Chart choice: the real 190-account Atrium seed at `scripts/core/data/atrium_coa_seed.json`. All 190 codes are present. His module boot added 10 control accounts that the seed does not contain (5030, 2080–2086, 9010, 9020), so the table count is 200. Account types present: Asset, Liability, Equity, Revenue, Expense, Statistical. Departments: his six USALI codes, because the seed is accounts only.

| Table | Count |
| --- | --- |
| `journal_headers` | 0 |
| `journal_lines` | 0 |
| `owner_pool_units` | 0 |
| `inventory_items` | 0 |
| `users` where id is `usr-controller-1` | 0 |

Dashboard on the post-commit sidecar: `propertyConfigured` false, `propertyName` empty, posted journals, revenue, and spending 0 for today and the period. Journals `[]`. The 18 production TEST/REVERSAL journals are not in this database.

Five template users from his role fixtures remain in the user table (`usr-accountant-1`, `usr-front-desk-1`, `usr-ap-buyer-1`, `usr-gm-1`, `usr-auditor-1`) plus `PERS-ZAYEN` and `PERS-MATT`. Password login is 403 while `ATRIUM_BETA_MOUNT=1`. `/api/auth/me` returns only the assertion user.

## Module table

Re-scored for `/amg/finance` on this mount. "Mounted" means his screen is the product page. Empty means the beta database above.

| Module | Status now |
| --- | --- |
| Board and Approvals desk | Kept at `/amg/finance/lite` and `/api/amg/finance`. The product path is his app. |
| Command Centre | Mounted. `propertyConfigured` false. Posted figures 0. |
| Journal workbench | Mounted. Journal list empty. Approve, post, and reverse return 403. |
| General ledger | Mounted. No posted entries. |
| Chart of accounts | Mounted. 190 seed accounts plus 10 control accounts. No balances from the TEST/REVERSAL set. |
| Trial balance | Mounted. Zero amounts. |
| Reports, including USALI | Mounted. Screenshot shows the Rooms Revenue report with the empty books. |
| Inventory | Mounted. 0 items. |
| Accounts receivable and payable | Mounted. Item lists empty. Payment post returns 403. |
| Tax payment, bank, administration, user switch, password login | His routes exist. Zayen and Owner receive 403 on the sensitive set above. Manage Access and the simulator are hidden. |
| Cash, payment run, month-end close, night audit, GM flash, handoff | In his product shell where he built them. No commissioned feed and no sample history were loaded. |
| GGV and BZG finance | Configuration slots only, `enabled: false`. |

## Gaps

- No Financial Controller seat. Approve, post, pay, bank, and administration stay refused until Matt decides that seat.
- Backblaze B2 upload is not configured. His test records that missing B2 settings are not a configured upload.
- GGV and BZG are reserved configuration. Their books are not opened here.
- The five template users remain in his SQLite user table. They cannot sign in through Wolf, and password login is refused in this mode.
- `staff_ready` and `human_commissioned` stay false.
