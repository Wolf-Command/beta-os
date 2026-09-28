# STAFF ACCESS — 28 Sep 2026

Decision served: owner brief 28 Sep 2026 10:09 WITA. Extends Wolf Core. Beta `:8788` only. Production `:8787` stayed pid 15975. Beta was restarted from pid 40318 to pid 52888 (`scripts/serve_beta.py`) and came back HTTP 200 on `/api/health`. No money, bank, payment, ESB, or NAS write. No Cloudflare Access edit. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_staff_access_20260928.py` through `scripts/tests/run_guarded.py`. DEPLOYED ROUTE PROOF is unsigned and spoofed deny on pid 52888, plus `GET /signout` → 302. A seated Cloudflare 200 was not observed. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured.

## STAFF ACCESS — READY FOR HUMAN SIGN-IN

| Person | AuthIdentity | Role | Scope | Allowed | Explicitly denied | Human test required |
| --- | --- | --- | --- | --- | --- | --- |
| Haikal (`PERS-HAIKAL`, unchanged) | `haikalqilbari123@gmail.com` (existing) | Creative Director, primary `ASG-HAIKAL-CD-1` still ACTIVE. Video Editor stays ENDED | Existing Creative Director scopes, including all content brands | Existing Creative Director grants, plus the content floor: `work.read`, `work.update`, `work.assign`, `evidence.record.submit`, `approval.request` | Finance, payment, bank change, Owner command, system admin. `content.plan.approve` stays off this role | Sign in. Expect Content (`/content-2.0`) and My Work as Creative Director. No finance, HR, or Owner command |
| Misa (`PERS-MISA`, not duplicated) | `mlsary111@gmail.com` (existing; case-normalised) | Creative Director primary `ASG-MISA-CD-1` on `POS-GGV-CREATIVE-DIRECTOR-2`. Content Crew `ASG-MISA-CC-1` stays ACTIVE and is not primary. AMG day fixture stays ACTIVE and is not primary | Creative Director scopes already on that role: GGV content, content library, all content brands, Habitat lead, CRM Habitat lead | Creative Director role grants. The still-active Content Crew assignment still adds that role's older grants. A replacement seated only on Creative Director does not receive the crew grants | `payment.approve`, `payment.execute`, `finance.nota.read`, progress, Owner command | Sign in. Expect Content, not the hotel desk. My Work says Creative Director. Crew and the AMG fixture are still on the person |
| Yudi | `widiatmika.11@gmail.com` | Content Creator, primary | `SCOPE-GGV-CONTENT`, `SCOPE-GGV-CONTENT-LIBRARY` | `content.plan.read`, `content.asset.upload`, `evidence.record.submit`, `approval.request`, `work.read`, `work.update` | Approve, publish, `work.assign`, finance, payment, bank, HR, governance, Owner, system admin, Uma close, AMG day operator | Sign in. Expect Content and My Work as Content Creator. Today is empty until work is stored on the assignment |
| Gery | `mr.gerryarfanata@gmail.com` | Content Creator, primary | same as Yudi | same as Yudi | same as Yudi | same as Yudi |
| Alam | `alamprojects26@gmail.com` | Content Creator, primary | same as Yudi | same as Yudi | same as Yudi | same as Yudi |
| TJ | `tejasaputra.wahyuhidayat@gmail.com` | Content Creator, primary | same as Yudi | same as Yudi | same as Yudi | same as Yudi |
| Nata | `omnia.folio@gmail.com` | Content Creator, primary | same as Yudi | same as Yudi | same as Yudi | same as Yudi |
| Rapp | `evetrovert@gmail.com` | Content Creator, primary | same as Yudi | same as Yudi | same as Yudi | same as Yudi |
| Not in the registry | `laluzayen@gmail.com` — not created | Not assigned. No person matched this email or a stored Zayen / Atrium Finance name. Display name was not invented. The only finance seat remains `ROLE-GGV-EXTERNAL-ACCOUNTANT` / `POS-GGV-EXT-ACCT`, still empty. There is no Atrium finance role | none | none | n/a — no identity | Confirm the existing person, or authorise a display name, before this email is bound. Do not add it to Cloudflare Access until then |

Legal names were not invented. Content Creator display names are the short names given.

## HR mailbox rows

These are function mailboxes in `org_function_mailboxes`. They are not Persons, not AuthIdentities, and not Wolf logins. No HR role exists, so no human was granted HR.

| Function | Address | Wolf login | Person | AuthIdentity |
| --- | --- | --- | --- | --- |
| HR | `hr@atriumlombok.com` | no | none | none |
| RECRUITMENT | `recruitment@atriumlombok.com` | no | none | none |

Do not add these two addresses to Cloudflare Access as Wolf users. Access to HR work has to come from an authorised human's active HR assignment. That assignment does not exist yet.

## Succession

On a temp copy of the catalog, not the live file: Yudi's active assignment was ended and `content.plan.read` became deny. The ended row stayed. A replacement person on a new Content Creator seat with the same role and the same two scopes could read and was denied `finance.nota.read`. The original person no longer had an active seat. My Work for the replacement was Content Creator.

## My Work

No work item is stored (`core_work_items` count stayed 0). Content Creator and Creative Director Today says: no content work is assigned to this seat yet; plans, submissions, and production tasks for this role will appear when they are stored on the assignment. Stored content plans were not copied into the queue. They are not assigned to these seats.

## Deployed Beta pid 52888

Unsigned `GET` is 403 on `/content-2.0`, `/my-work`, `/api/staff/home`, `/ggv/finance`, `/wolf`, `/api/owner/command`, `/bzg/uma-blu`, `/amg-ops-pack`, and `/progress`. A spoofed `X-Wolf-Subject` and a spoofed `Cf-Access-Authenticated-User-Email` are 403. `GET /signout` is 302 to the Access logout. A seated allow was not minted.

## Cloudflare Access include list

Human / Owner step. This pack did not edit Cloudflare.

Add these bound personal emails if they are not already on the Beta Access include list:

- `haikalqilbari123@gmail.com`
- `mlsary111@gmail.com`
- `widiatmika.11@gmail.com`
- `mr.gerryarfanata@gmail.com`
- `alamprojects26@gmail.com`
- `tejasaputra.wahyuhidayat@gmail.com`
- `omnia.folio@gmail.com`
- `evetrovert@gmail.com`

Do not add `hr@atriumlombok.com` or `recruitment@atriumlombok.com`.

Do not add `laluzayen@gmail.com` until a Person is bound.

## Tests

| suite | result |
| --- | --- |
| `test_staff_access_20260928.py` | SUMMARY pass=204 fail=0 |
| `test_canonical_guard.py` | PASS=20 FAIL=0 |
| `test_role_dashboard.py` | PASS=142 FAIL=2. Owner succession fingerprint and the HTTP owner succession. The same two were already recorded this morning. Creative, F&B, finance, closer, and manager fingerprints passed. Misa's primary page is not the manager page |
| `test_staff_home.py` | The checks through the owner pulse passed. The suite then deletes a scratch row in the live catalog. The guard refused that write (`not authorized`) and the process stopped. Not re-run a second time |
| `test_wolf_intel_nav.py` | PASS=160 FAIL=5. Misa landing checks passed. Remaining: content crumb string is not in `content-2.0.html` (that file was not edited), and three prior-wave child suites |
| `test_wolf_amg_nav.py` | PASS=142 FAIL=3. Misa landing and bake checks passed. Remaining fails are prior-wave child suites |

`test_rbac_permissions.py` was not run. It writes the live catalog. The inactive-assignment check now ends every active Misa assignment, then restores those rows, so a second seat cannot leave access on.

## Commits

Local only. Not pushed. `4270103` seats the identities. This file's hash follows that commit.

RESULT: PASS
