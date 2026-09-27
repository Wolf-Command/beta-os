# One walk — 28 Sep 2026

This is the human half left after pack F2. It does not raise SYSTEM. It does not mark staff ready or human commissioned. A person writes the statuses. Cursor does not fill them in.

Do this on `https://beta.wolfcommand.net` in a normal browser. One sign-in per person. Stay signed in until that person's last step, then sign out. Open each URL in the address bar. Write down the HTTP status if the browser shows it, otherwise write what the page did (the page loaded, or it asked you to sign in, or it refused you).

Capture: one text note per person, dated, with the fields below. Keep the note. That note is the reusable evidence for every capability the step lists. A screenshot can sit beside the note. The note is the record. Do not mark a capability commissioned from the note until the statuses are written.

Amanda is not in this walk. Matt's session is the allow side for organisation, assignments, work items, approvals, and Owner Command. Haikal and Devi are the deny side for those reads.

The job on each desk is in `docs/wolf/five/HUMAN-SCENARIOS.md`. Do that job in this same sign-in. Do not sign in a second time for the same person. Haikal does the content steps after step 1, before step 2. Devi does the Uma steps after step 1, before step 2. Matt does the finance steps after step 4, before step 11. Amanda is a separate sign-in only if she is the one holding the nota photo. Do not open the Atrium books in this walk.

## Haikal

Sign in. You should land on Content.

| step | open | proves | write down |
| --- | --- | --- | --- |
| 1 | the page you land on | CAP-CORE-02 landing, CAP-CORE-04 content allow | the path |
| 2 | `/bzg/uma-blu` | CAP-CORE-04 deny | refused or not |
| 3 | `/wolf` | CAP-CORE-04 deny | refused or not |
| 4 | `/ggv/finance` | CAP-CORE-04 deny | refused or not |
| 5 | `/api/core/entities` | CAP-CORE-01 deny. This seat does not hold `organisation.entity.read` | status, and that no entity list was shown |
| 6 | `/api/core/persons/PERS-HAIKAL/assignments` | CAP-CORE-03 deny. This seat does not hold `organisation.role.read` | status, and that the assignment list was not shown |
| 7 | Sign out, then open `/content-2.0` | CAP-CORE-02 sign-out | asked to sign in, or not |

## Devi

Sign in. You should land on Uma Blu.

| step | open | proves | write down |
| --- | --- | --- | --- |
| 1 | the page you land on | CAP-CORE-02 landing, CAP-CORE-04 Uma allow | the path |
| 2 | `/content-2.0` | CAP-CORE-04 deny | refused or not |
| 3 | `/wolf` | CAP-CORE-04 deny | refused or not |
| 4 | `/ggv/finance` | CAP-CORE-04 deny | refused or not |
| 5 | `/api/core/entities` | CAP-CORE-01 deny | status, and that no entity list was shown |
| 6 | `/api/core/persons/PERS-HAIKAL/assignments` | CAP-CORE-03 deny | status, and that the assignment list was not shown |
| 7 | Sign out, then open `/bzg/uma-blu` | CAP-CORE-02 sign-out | asked to sign in, or not |

## Matt

Sign in. You should land on Wolf.

| step | open | proves | write down |
| --- | --- | --- | --- |
| 1 | the page you land on | CAP-CORE-02 landing, CAP-CORE-04 Wolf allow | the path |
| 2 | `/content-2.0` | CAP-CORE-04 content allow | loaded or refused |
| 3 | `/bzg/uma-blu` | CAP-CORE-04 Uma allow | loaded or refused |
| 4 | `/ggv/finance` | CAP-CORE-04 finance allow | loaded or refused |
| 5 | `/api/core/entities` | CAP-CORE-01 allow. This seat holds `organisation.entity.read` | status, and whether an entity list is present |
| 6 | `/api/core/entities/ENT-GGV` | CAP-CORE-01 one entity read | status, and the entity id if shown |
| 7 | `/api/core/persons/PERS-HAIKAL/assignments` | CAP-CORE-03 allow | status; whether `ASG-HAIKAL-CD-1` is ACTIVE; whether `ASG-HAIKAL-VE-1` is not active |
| 8 | `/api/core/work-items` | CAP-CORE-06 seated read of the live list | status and the count. The live table was 0 when F2 ran. Write the count you see. Do not add a work item to make it non-zero |
| 9 | `/api/core/approvals` | CAP-CORE-07 seated read of the live request list | status and the request count. The live request table was 0. This step does not approve a wide policy |
| 10 | `/api/owner/command` | CAP-CORE-09 classification and CAP-CORE-10 stored exceptions | status; evidence `valid_operational` and `invalid_test`; exception `valid_operational_count` and `invalid_test_count`; the exception ids and their statuses. F2 left evidence total 4 with valid operational 0, and three REJECTED exceptions with valid operational 0. `cadence_done` should still be false. Do not mark the cadence done. One look is not the cadence |
| 11 | Sign out, then open `/wolf` | CAP-CORE-02 sign-out | asked to sign in, or not |

Do not delete evidence `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153`. Do not delete exception `GEX-41967006-311f-4ab0-9802-1e6db54ce18e`.
