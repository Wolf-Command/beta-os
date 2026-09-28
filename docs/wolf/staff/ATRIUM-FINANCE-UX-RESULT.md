# ATRIUMFIN-UX-1 — Atrium Finance staff UX

Decision served: owner brief 28 Sep 2026 11:28 WITA (staff access), extended on the existing Atrium Finance desk. Beta `:8788` only. Production `:8787` pid 15975 was not restarted. No grant, role, or person-specific role was added. `staff_ready` and `human_commissioned` stay false. Human retest #2 is PENDING.

## Capabilities found

Checked against `ROLE-AMG-FINANCE-OFFICER` in `scripts/core/staff_access.py` and the Beta routes. Zayen's only active role is that one. Scope is `SCOPE-AMG-FINANCE` / `ENT-AMG`.

Shown, because the grant and the route both exist:

| Desk | Grant | Route | What she sees |
| --- | --- | --- | --- |
| Board | `atrium.board.read` (`PERM-ATRIUM-BOARD-READ`) | `GET /amg/finance`, `GET /api/amg/finance` | Empty state. `read_accounting_core` reports the books are not open and `consolidation_figure` is absent, so the page does not show a number. |
| Approvals | `approval.request` (`ATRIUM_SUBMIT`) | `GET /amg/finance/approvals`, `GET` and `POST /api/amg/finance/approvals` | Her own Atrium requests only. The live list is empty. She can send a general decision. `approval.decide` is not granted, so she does not approve it. The page says "Approvals are handled by the Finance Controller." |

Not shown. The grant is stored and the Beta route is not:

| Id | Grant | Why it stays off the nav |
| --- | --- | --- |
| ledger | `atrium.ledger.read` | No journal table. No `/api/journals`, `/api/ledger`, or `/api/trial-balance`. |
| chart | `atrium.coa.read` | No chart table. No `/api/accounts`. |
| reports | `atrium.report.read` | No `/api/reports/financial-statements`, `/api/reports/usali`, or `/api/reports/drilldown`. `/api/fin/mgmt-reporting` is Owner (`PERS-MATT`, `progress.read`) only. |
| journal | `atrium.journal.draft` | No journal table and no `POST /api/journals`. `atrium.journal.approve` and `atrium.journal.post` stay in `ATRIUM_HELD_BACK`. |

`ATRIUM_DENIED` still includes `payment.approve`, `payment.execute`, `vendor.bank.change`, `approval.decide`, `finance.policy.admin`, `organisation.role.read`, and `core.operator`.

## What changed

- `dashboards/amg-finance.html` is the Atrium Finance desk: header "Atrium Finance", entity Atrium, Board and Approvals only, empty states, and a decision form with no amount. The four engineering sentences are gone from this page and from `GET /api/amg/finance`.
- `scripts/core/atrium_finance_desk.py` reads the board and lists or submits her own general approval request. Submit forces `ENT-AMG`, `GENERAL`, and `approval.decide` as the required permission. Amount, payment, bank, journal, approve, and post fields are refused.
- `scripts/serve_beta.py` serves the page and `GET/POST /api/amg/finance/approvals`. `POST /api/amg/finance` stays 405.
- `scripts/core/staff_access.py` allows the approvals path on the existing Atrium wall. The grant list is unchanged.
- `scripts/core/fin_entity_boards.py` and `dashboards/amg-ops-pack.html` were not edited. The ops-pack sentence stays for the existing board check and is listed in the audit.

ZAYENFIX-1 routing is unchanged: a signed-in `/` is 302 to `/amg/finance`, a browser page denial is HTML, and `/api` stays JSON 403.

## Tests

`python3 scripts/tests/run_guarded.py` on 28 Sep 2026:

| Suite | Result |
| --- | --- |
| `scripts/tests/test_atrium_finance_ux_20260928.py` | SUMMARY pass=77 fail=0 |
| `scripts/tests/test_role_routing_20260928.py` | SUMMARY pass=84 fail=0 |
| `scripts/tests/test_staff_access_20260928.py` | SUMMARY pass=274 fail=0 |
| `scripts/tests/test_ggv_finance_invoice_20260928.py` | PASS=92 FAIL=0 |
| `scripts/tests/test_ggv_finance_mobile_nota.py` | PASS=138 FAIL=0 |
| `scripts/tests/test_ggv_finance_nota_storage_accountant.py` | PASS=100 FAIL=0 |
| `scripts/tests/test_zarah_frail_cd_20260928.py` | SUMMARY pass=150 fail=0 |

The Atrium suite checks the banned strings, that nav matches Board and Approvals, and the 403s for GGV, Blu Zone, Owner, roles, journal approve/post, pay, bank change, and approval decide. Amanda is 403 on both Atrium pages. A general request on a temp catalog copy returns 201 and does not move money. The live approval-request count is unchanged by that test.

## Deployed route

Beta listener is pid 73997, `scripts/serve_beta.py`, port 8788. Production pid 15975 on 8787 was still that process after the restart.

Live Beta is `BETA_AUTH_MODE=cloudflare_access`. `X-Wolf-Subject` is ignored, the same way the other staff tests treat a process that was not started in `development_assertion`. This session, against `http://127.0.0.1:8788`:

- `GET /api/health` 200
- unsigned `GET /` and `GET /amg/finance` 403 HTML Access denied
- `X-Wolf-Subject: laluzayen@gmail.com` on `/amg/finance` and `/amg/finance/approvals` 403 HTML Access denied
- the same header on `/api/amg/finance`, `/api/core/roles`, `/ggv/finance`, `/bzg/uma-blu`, `/wolf`, pay, and bank 403 `missing_auth` (`Cf-Access-Jwt-Assertion required`)
- the same header on `POST /api/journals/sample/approve` and `POST /api/journals/sample/post` 404 `not found`, because the Atrium wall runs only after identity is accepted and those routes are not registered

Signed proof uses the staff-test path (`BETA_AUTH_MODE=development_assertion`, header `X-Wolf-Subject: laluzayen@gmail.com`) inside `test_atrium_finance_ux_20260928.py`. There, `/amg/finance` and `/amg/finance/approvals` are 200 HTML, the API figure is null, `staff_ready` and `human_commissioned` are false, and the forbidden routes above are 403, including journal approve and post.

Live Beta was not switched to `development_assertion`.

## Screenshots

Rendered with headless Chrome DevTools device metrics against that same signed test handler, not against the Cloudflare listener.

- `docs/wolf/staff/shots/atrium-finance-desktop.png` — 1440×900. Layout `scrollWidth` 1440, `clientWidth` 1440. Approvals control height 44.
- `docs/wolf/staff/shots/atrium-finance-phone.png` — 390×844. Layout `scrollWidth` 390, `clientWidth` 390. Approvals control right edge 374, height 44.

## Audit

Report only, in `docs/wolf/staff/STAFF-PLACEHOLDER-AUDIT.md`. Same class of copy remains on `dashboards/amg-ops-pack.html`, `scripts/core/fin_entity_boards.py`, `dashboards/ggv-finance.html`, `dashboards/ggv-ops-pack.html`, `dashboards/content-2.0.html`, `dashboards/bzg-uma-blu.html`, `dashboards/uma-blu-close.html`, and `scripts/core/staff_home.py`. None of those pages were rebuilt.

## Commissioning

Zayen's card in `docs/wolf/staff/HUMAN-COMMISSIONING-28SEP.md` is RETEST #2 PENDING. FAIL #1 and FAIL #2 stay on record. No human login was recorded.

RESULT: PASS
