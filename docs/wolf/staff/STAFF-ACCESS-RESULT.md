# STAFF ACCESS — 28 Sep 2026

Decision served: owner brief 28 Sep 2026 11:28 WITA. Extends STAFF-1 on commit `d97ea20`. Beta `:8788` only. Production `:8787` stayed pid 15975. Beta was restarted from pid 52888 to pid 58853 (`state/build-factory/detach.py` then `scripts/serve_beta.py`). Health on `:8788` is HTTP 200. No money, bank, payment, ESB, or NAS write. No Cloudflare Access edit. No push. Grok was not called. Atrium books were not opened. Authority limits stay 0. SoD constraints stay 0.

STAFF READY is false for every person. HUMAN COMMISSIONED is false for every person. This pack is not a new git commit.

The first Beta restart loaded the old role seed and put Misa's Content Crew assignment back to ACTIVE. The seed now leaves an ended assignment ended. The assignment was ended again, Beta was restarted once more, and the row stayed ENDED.

## STAFF ACCESS — HUMAN TESTING OPEN

| Person | Role | Scope | Beta Access (CF include: PENDING OWNER unless verified) | Landing Page | Allowed | Denied | Commissioning Status (PENDING) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Haikal | Creative Director, primary | Existing Creative Director scopes | PENDING OWNER | `/content-2.0` | Content floor already on that role: read and update work, assign work, submit evidence, request approval | Finance, payment, bank, Owner, system admin | PENDING |
| Misa | Creative Director, primary | Same Creative Director scopes as that role | PENDING OWNER | `/content-2.0` | Creative Director grants. Content read still allowed | Payment, bank, Owner, the ended crew grants, hotel day operator | PENDING |
| Zarah | Creative Director, primary | Same Creative Director scopes as Haikal | OWNER ADDED | `/content-2.0` | Same Creative Director grants as Haikal: content read and update, upload, assign, review, submit evidence, request approval | Finance, HR, payment, bank, Owner, system admin, hotel day, BZG ops. Publish stays on the Publish Gate | PENDING |
| Frail | Creative Director, primary | Same Creative Director scopes as Haikal | OWNER ADDED | `/content-2.0` | same as Zarah | same as Zarah | PENDING |
| Yudi | Content Creator, primary | GGV content and the content library | PENDING OWNER | `/content-2.0` | Read plans, upload, submit evidence, request approval, read and update work | Approve, publish, assign work, finance, payment, bank, Owner, system admin | PENDING |
| Gery | Content Creator, primary | same as Yudi | PENDING OWNER | `/content-2.0` | same as Yudi | same as Yudi | PENDING |
| Alam | Content Creator, primary | same as Yudi | PENDING OWNER | `/content-2.0` | same as Yudi | same as Yudi | PENDING |
| TJ | Content Creator, primary | same as Yudi | PENDING OWNER | `/content-2.0` | same as Yudi | same as Yudi | PENDING |
| Nata | Content Creator, primary | same as Yudi | PENDING OWNER | `/content-2.0` | same as Yudi | same as Yudi | PENDING |
| Rapp | Content Creator, primary | same as Yudi | PENDING OWNER | `/content-2.0` | same as Yudi | same as Yudi | PENDING |
| Zayen | Atrium Finance Officer, primary. The role is not named for her | Atrium only (`ENT-AMG`) | PENDING OWNER | `/amg/finance` | Read the board, read the ledger, save a draft journal in the ledger app's terms, read reports, read the chart, submit for approval | Post or approve a journal, pay, approve a payment, bank change, GGV, Blu Zone, Owner, system admin, role admin, hotel day desk. No limit was granted | PENDING/FAIL |

Login cards are `docs/wolf/staff/HUMAN-COMMISSIONING-28SEP.md`. Every human result there is PENDING except Zayen, who is PENDING/FAIL until she retests. Zarah and Frail use the existing Creative Director card.

Zayen Atrium Finance Officer — HUMAN FAIL 28 Sep 13:18 WITA — raw JSON on /; repair ZAYENFIX-1; retest PENDING

## Zayen

Person `PERS-ZAYEN`. Display name Zayen. No surname. Email `laluzayen@gmail.com`.

No Atrium finance role was already in Wolf. The ledger app's General Accountant is a role inside that app, not a Wolf assignment. One Wolf role was created: `ROLE-AMG-FINANCE-OFFICER`, label Atrium Finance Officer. Position `POS-AMG-FINANCE-OFFICER-1`. Assignment `ASG-ZAYEN-FIN-1`. Scope `SCOPE-AMG-FINANCE` targets `ENT-AMG` only.

Grants follow the ledger routes in `atrium-finance/server/routeAccess.ts`:

- Board read is `GET /api/dashboard`.
- Ledger read is `GET /api/journals`, `GET /api/journals/:id`, `GET /api/ledger`, and `GET /api/trial-balance`.
- Draft save is `POST /api/journals` and `POST /api/journals/:id/validate`.
- Report read is `GET /api/reports/financial-statements`, `GET /api/reports/usali`, and `GET /api/reports/drilldown`.
- Chart read is `GET /api/accounts`.
- Submit for approval is the existing `approval.request` on Atrium only.

Journal approve and journal post exist as codes and are not granted. Those routes require approve. The ledger app has no source-document upload route, so no upload grant was created. The Wolf page does not open the books and does not save a journal.

On a temp copy of the catalog: ending Zayen's assignment removed access and kept the row on her. A replacement on the same role and the same scope could read the board and was denied payment and GGV.

## Misa

Content Crew `ASG-MISA-CC-1` was created `2026-09-16T21:47:39+08:00` by the role seed. Role `ROLE-CONTENT-CREW`, position `POS-CONTENT-CREW-1`, label Content Crew (TBD title). It was not primary. Scopes were GGV content, the content library, Habitat lead, and CRM Habitat lead. Its grants included publish request, lead operator, and organisation read. The Creative Director role does not have those grants. Haikal, who is only on Creative Director, does not have them. No live Creative Director step depends on the crew seat. It is ended. End `2026-09-28T11:47:45+08:00`. The row remains. Reason: Content Crew is a 16 Sep 2026 TBD seed. Creative Director is the live seat. The crew grants are not on that role. Ended so the old seat does not keep access.

The hotel day seat `ASG-AMG-DAY-MISA` was created `2026-09-22T14:17:42+08:00` by the day-operator fixture. Role General Manager, position Atrium day-operator Beta fixture, scope AMG Atrium day operator. The only grant was `amg.day.operator`. The code says it is not live hotel commissioning. It is ended. End `2026-09-28T11:44:52+08:00`. The row remains. A later day-operator ensure does not put the ended row back. Reason: Atrium day-operator seat is a Beta fixture from 22 Sep 2026, not a live hotel assignment. Ended so hotel day access does not stay on this person.

Misa's primary is still Creative Director. She still lands on Content. She can still read content. Payment and the hotel day permission are denied.

## My Work

`core_work_items` stays 0. The nine stored content plans were not assigned to these seats. Today stays empty.

## Deployed Beta pid 58853

Unsigned `GET` is 403 on `/amg/finance`, `/content-2.0`, `/ggv/finance`, `/bzg/uma-blu`, `/wolf`, and `/amg-ops-pack`. A spoofed subject and a spoofed access email are 403. `GET /signout` is 302. A seated Cloudflare allow was not minted.

Do not add `hr@atriumlombok.com` or `recruitment@atriumlombok.com`.

Add `laluzayen@gmail.com` to the Beta Access include list only when the Owner does that step. This pack did not.

## Tests

| suite | result |
| --- | --- |
| `test_staff_access_20260928.py` | SUMMARY pass=274 fail=0 |

The count includes the allow and deny matrix, direct-URL denies, the Content Creator succession, and the Atrium Finance Officer succession.

## Commits

Local only. Not pushed. Parent remains `d97ea20`. This pack is not committed.

## STAFF-3 — Zarah and Frail

Owner directive 28 Sep 2026 13:34 WITA. Extends this staff registry. Not a new role and not a new system. Beta `:8788` only. Production `:8787` stayed pid 15975. No Cloudflare edit. The Owner had already added both emails to the Beta Access include list.

No Person and no AuthIdentity existed for either email or for the names Zarah, Frail, Lestrange, or Bongat. New rows were created. They were not duplicates.

| Person | AuthIdentity | Assignment | Position |
| --- | --- | --- | --- |
| Zarah `PERS-ZARAH` | `AUTH-ZARAH-EMAIL` `zarah.lestrange@gmail.com` | `ASG-ZARAH-CD-1` primary ACTIVE | `POS-GGV-CREATIVE-DIRECTOR-3` |
| Frail `PERS-FRAIL` | `AUTH-FRAIL-EMAIL` `frail.bongat@icloud.com` | `ASG-FRAIL-CD-1` primary ACTIVE | `POS-GGV-CREATIVE-DIRECTOR-4` |

Both sit on `ROLE-GGV-CREATIVE-DIRECTOR`. That role was not changed. Haikal `ASG-HAIKAL-CD-1` stays ACTIVE and primary. Detail is `docs/wolf/staff/ZARAH-FRAIL-RESULT.md`.

Beta was restarted from pid 68812 to pid 71613 (`state/build-factory/detach.py` then `scripts/serve_beta.py`). Health on `:8788` is HTTP 200. Unsigned `/` is HTTP 403. Production `:8787` stayed pid 15975.

STAFF READY is false. HUMAN COMMISSIONED is false. Commissioning stays PENDING.

RESULT: PASS
