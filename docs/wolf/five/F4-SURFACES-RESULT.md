# F4 — Four surfaces, staff eye — 28 Sep 2026

Pack F4 of the five-pack sprint. Owner brief 28 Sep 2026 06:46 WITA, item 4. Extends the existing Content, Uma Blu, GGV Finance, and Atrium desks. This is not a new system. Beta/local only. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` was restarted from pid 25471 to pid 28954 (`scripts/serve_beta.py`) so the bills and issues gate is the process that serves the route. It came back on `:8788`. No money, bank, payment, ESB, or NAS write. No nota, vendor, person, or assignment was inserted. No Atrium book was opened. No secret value is in this note. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_f4_surfaces.py` run through `scripts/tests/run_guarded.py` on a temp catalog copy, plus the suites below. Those 200s use a development subject on an ephemeral handler. They are not a Cloudflare session on pid 28954. DEPLOYED ROUTE PROOF is unsigned 403 on pid 28954, and 302 to the Access login on `https://beta.wolfcommand.net`. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

The jobs are `docs/wolf/five/HUMAN-SCENARIOS.md`. They sit inside `docs/wolf/five/ONE-WALK.md` for Haikal, Devi, and Matt. Amanda signs in only if she is the one holding the nota photo.

## Seats, from the registry

| surface | role | person on an active assignment |
| --- | --- | --- |
| Content Engine | `ROLE-GGV-CREATIVE-DIRECTOR` | Haikal, `ASG-HAIKAL-CD-1`, primary |
| Uma Blu operations | `ROLE-BZG-FB-OPS-LEAD` | Devi, `ASG-DEVI-FB-OPS-1`, primary |
| GGV Finance notas and vendors | `ROLE-CONTENT-MGMT` and `ROLE-MATT` | Amanda, `ASG-AMANDA-CM-1`, primary. Matt, `ASG-MATT-OWNER-1`, primary |
| GGV external accountant | `ROLE-GGV-EXTERNAL-ACCOUNTANT` | nobody. `POS-GGV-EXT-ACCT` stays empty |
| Atrium Finance | `role-financial-controller` in the Atrium source seed | nobody stored |

The uncommissioned Atrium database has 0 users and 0 roles. That count is the user and role tables only. Journals, revenue, and spending were not read. Wolf has no Atrium finance assignment. Misa's active `ROLE-AMG-GM` assignment is not primary, and that role holds `amg.day.operator`. It is not the books. The hotel desk Finance item has no address. The line on the page is "Hotel books are not open on this desk."

## What changed

- Content plan list no longer prints the raw lane word. A test-lane plan, if one is opened, says "Practice plan". The default list is still operational only. The three test-lane plans were not deleted.
- Uma Today says "No stock count is on this screen. Stock stays in ESB." It does not say "empty framework". A connective item opens as "Open", and only to a page address.
- Bills and issues now use the same sign-in gate as Today. Unsigned is 403. Practice purchase requests are not listed. The three example rows are still in `bzg_ops_purchase_requests`. They are not shown as live work. Purchasing still lands on the bills page anchor.
- GGV Finance overview says "Not paid from this screen". Notas are 0. Vendors are 0. The empty lines are "Nothing added yet." and "No vendors yet."
- Petty cash HTML is still reachable unsigned. The petty API is 403 without a sign-in. `test_uma_petty_cash.py` requires that split. It was not changed.

Phone width was 390, and bills was also checked at 430. Desktop was 1280. No sideways scroll on those renders. The content check is the plan view with Library and Upload on the page. A seated search of the library was not clicked.

## Deployed Beta pid 28954

Unsigned, no document:

| path | status |
| --- | ---: |
| `/content-2.0` | 403 |
| `/bzg/uma-blu` | 403 |
| `/bzg/uma-blu/bills` | 403 |
| `/bzg/uma-blu/issues` | 403 |
| `/ggv/finance` | 403 |
| `/amg-ops-pack` | 403 |
| `/bzg/uma-blu/petty` | 200 |

On `https://beta.wolfcommand.net`, `/content-2.0`, `/bzg/uma-blu/bills`, and `/ggv/finance` are 302. The finance response is `server: cloudflare` and `www-authenticate` starting `Cloudflare-Access`. The login query string was not recorded.

Live catalog after the pack: evidence 4, exceptions 3, governance policies 1, notas 0, vendors 0, purchase requests 3, of which 3 are examples.

## Suites

The first run of `test_f4_surfaces.py` counted every line as pass because the assertion arguments were reversed. The log still showed unsigned `/bzg/uma-blu/bills` as 200. That was the repair: the checker, and the bills and issues gate. One re-run after that.

| suite | result |
| --- | --- |
| `test_f4_surfaces.py` | PASS=79 FAIL=0 |
| `test_content_engine_staff_ux.py` | PASS=54 FAIL=0 |
| `test_uma_petty_cash.py` | PASS=53 FAIL=0 |
| `test_wolf_amg_nav.py` | PASS=144 FAIL=3 |

The three AMG nav failures are the child checks "soft prior wave1 shell-tokens", "soft prior wave2 empire-home", and "soft prior wave4 ggv-nav". Their output includes `test process refuses canonical Beta write`. The Finance · EMPTY check in that file was not one of the three failures. Those children were not repaired. The guard lines are the F1 refusal. They are not a seated allow.

Listeners after the restart: pid 15975 is still `serve.py` on `:8787`. pid 28954 is `scripts/serve_beta.py` on `:8788`.

RESULT: PASS
