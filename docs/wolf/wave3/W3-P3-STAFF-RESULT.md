# W3-P3 — Role dashboards and staff operating experience (/my-work) — 27 Sep 2026

Decision served: owner brief 27 Sep 2026, PACK 3. Extends the staff home (`docs/wolf/sprint7/P3-STAFFHOME-RESULT.md`) and the Pack 4 truth layer (`docs/wolf/wave3/W3-P4-TRUTH-RESULT.md`). Not a new task or approval database.

TECHNICAL PROOF is separate from DEPLOYED ROUTE PROOF, and both are separate from STAFF READINESS, HUMAN COMMISSIONING, and OPERATING ADOPTION.

Production `:8787` stayed on pid 15975 (`serve.py`). Beta `:8788` was restarted with `launchctl kickstart -k` on `gui/501/net.wolfcommand.serve-beta` only, from pid 31422 to pid 33401, still `scripts/serve_beta.py`. No money, bank, or payment action. No NAS write. No external call. No ledger write.

## BEFORE

`/my-work` was one role page with four questions for staff and six pulse lines for the Owner. It did not project a shared role dashboard from Person, Role, Assignment, Scope, Permission, and Audience. It had no closer desk, no general-manager desk, and no responsibilities block that refuses a made-up performance figure. The daily close page was served to any signed-in person, including a Creative Director.

## BUILT

- `scripts/core/role_dashboard.py` is a projection. It does not add a table. Person is the greeting only. Role, assignment, scope, permission, and audience pick the page.
- Sections on `/my-work`: Today, Do this, Needs attention, Waiting, Recently completed, My responsibilities. The older question lines stay inside those sections so the existing staff-home proof still reads them.
- Do this is the one real next link for that role. There is no second link into another company's work.
- My responsibilities is plain language from the role, the assignment covers, and the permission boundary. Performance is MISSING. `shown_as_score` is false. No number is shown.
- The page uses the shared `#wolfnav` shell and the Pack 4 stamp (`data-surface="my-work"`). Wolf Core CURRENT means the control store was read. It is not a performance score and it is not commissioned.
- `staff_ready`, `human_commissioned`, and `operating_adoption` are false.
- Direct `/uma-blu-close` is limited to the closer, F&B operations lead, Head of F&B, and Owner roles. A Creative Director and a General Manager are refused.

Representative map, from the catalog roles, not from person names:

| brief name | catalog role | live seat | desk |
| --- | --- | --- | --- |
| Creative Director | `ROLE-GGV-CREATIVE-DIRECTOR` | Haikal, primary | Open the content library |
| BZG F&B Operations Lead | `ROLE-BZG-FB-OPS-LEAD` | Devi, primary | Open today's Uma Blu work |
| Finance | same row as external accountant | nobody | Open finance notes |
| external accountant | `ROLE-GGV-EXTERNAL-ACCOUNTANT` | nobody on `POS-GGV-EXT-ACCT` | Open finance notes |
| closer | `ROLE-BZG-CLOSER` | nobody on `POS-BZG-CLOSER-UMA-1` | Open today's close |
| manager | `ROLE-AMG-GM` (General Manager) | Misa is on this position, not as her primary assignment | Open the hotel desk |
| Owner | `ROLE-MATT` | Matt, primary | Owner pulse, no staff desk |

There is no second finance role in the catalog. Finance and external accountant are one seat: read and review notes, no pay, no bank change, no governance authority.

Misa's primary assignment is Content Crew. My Work for her is that content seat, not the General Manager page. The manager page was proved by a temporary primary assignment on `ROLE-AMG-GM`, then removed. Her shell audience is still the older person map. That map was not changed.

Read after the repair, from the local catalog, not from a manufactured score:

| seat | today | do this | attention | waiting | completed | performance |
| --- | --- | --- | --- | --- | --- | --- |
| Creative Director | EMPTY | content library | EMPTY | EMPTY | EMPTY | MISSING |
| BZG F&B Operations Lead | EMPTY | Uma Blu today | EMPTY | EMPTY | EMPTY | MISSING |
| Owner | EMPTY | EMPTY | EMPTY | EMPTY | EMPTY | MISSING |

EMPTY means the Wolf Core read returned no rows. It is not a claim that the day is fine. MISSING means no performance figure is stored. Responsibilities text is present. It is not a score.

`scripts/serve_beta.py` already held a large uncommitted rebuild. The close gate and the permission-denied component on My Work are in that working tree, which pid 33401 is running. They are not in the pack commit, so a checkout of the commit alone does not contain that gate.

## VERIFIED

```
python3 scripts/tests/test_role_dashboard.py | tail -3
PASS  temporary seats removed
PASS=144 FAIL=0
EXIT: SUCCESS
```

The first run failed before the HTTP section: scratch work used a work type the catalog rejects, the close page still opened for the Creative Director because a content scope can see the BZG entity, and the finance page in this test process returns 500 `live_write_refused` instead of serving HTML. One repair fixed the work type, limited the close page by role, and treated a non-HTML finance response as not served. The suite was then green.

Succession, temporary people removed afterwards: a replacement Creative Director matches Haikal, a replacement F&B lead matches Devi, two external-accountant seats match each other, two closers match each other, two general managers match each other, and a replacement Owner matches Matt. The fingerprint drops the person's name. A scratch work item is visible only to the person who owns it. A GGV item does not appear for the closer, the manager, finance, or the F&B lead. A BZG item does not appear for the creative seat or finance. An AMG item does not appear for the creative seat or the closer.

Headless Chrome on the ephemeral handler, no horizontal overflow: Creative Director at 390px and 1280px, F&B lead at 390px, closer at 390px, general manager at 390px, external accountant at 1280px, Owner at 390px and 1280px. Each page showed its own next action and hid the other roles' desks. Performance said "No performance figure is on record."

Unsigned and direct URL on that handler: `/my-work` and `/api/staff/home` are 403 `permission-denied`. POST is 405. Creative Director is 403 on the hotel desk, the content path is allowed for that role, and the close page is 403. Closer and manager are 403 on the content library. The closer can open `/uma-blu-close`. Finance is 403 on Uma Blu and on the content library. The finance notes URL was not served to closer, manager, or Creative Director (test process: 500 `live_write_refused`, no HTML).

Previously green suites, re-run in this session:

```
python3 scripts/tests/test_staff_home.py | tail -3
PASS=89 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_uma_daily_loop_finish.py | tail -3
PASS=47 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_owner_command.py | tail -3
PASS=66 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_dashboard_truth_provenance.py | tail -3
PASS=98 FAIL=0

python3 scripts/tests/test_dashboard_truth.py | tail -3
PASS=62 FAIL=0

python3 scripts/tests/test_owner_empire_pack.py | tail -3
PASS=80 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_wolf_bzg_uma_nav.py | tail -3
PASS=111 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_ggv_ops_pack.py | tail -3
PASS=97 FAIL=0
```

`test_amg_ops_pack.py` was already red in Pack 4 for a live roster fact (Misa on `ROLE-AMG-GM`). This pack does not change that seat, so that suite was not re-run.

Deployed on Beta `:8788` after the restart to pid 33401, unsigned:

```
/my-work            403  forbidden  ui.component permission-denied
/api/staff/home     403  forbidden  ui.component permission-denied
/uma-blu-close      403  forbidden  ui.component permission-denied
/content-2.0        403  forbidden
/ggv/finance        403  missing_auth
POST /api/staff/home 405  writes refused
```

Signed-in 200 was proved on the ephemeral handler with a development subject, not by bypassing the live Cloudflare gate. Production pid 15975 was still `serve.py` on `:8787` after the Beta restart. Beta pid 33401 is `scripts/serve_beta.py`.

## STAFF READY?

NO. `staff_ready` is false. A rendered My Work page is not a staff walk. Known seats still land on their older desks when they sign in. That landing was not switched.

## HUMAN COMMISSIONED?

NO.

## BLOCKERS

- No human evidence that any staff member has used this page.
- Wolf Core has no open work, approval, or exception for these seats. Today stays empty until a real record exists. This pack does not invent one.
- No performance figure is stored. MISSING is not a score.
- Nobody is seated on the closer position or the external accountant position. The proofs were temporary people, then removed.
- Finance and external accountant are one catalog role. A separate internal finance role was not created.
- Misa's primary assignment is Content Crew. Opening My Work as her does not show the General Manager page. The older shell map still labels her AMG. Neither was changed.
- Shell Home was not switched. Creative Director still lands on the content library, and the F&B lead still lands on Uma Blu today.
- The close gate and the permission-denied JSON are running from the dirty `scripts/serve_beta.py` working tree. That file was not committed, because it already contained the rest of the rebuild.

## NEXT HUMAN TEST

Sign in on Beta as the Creative Director and open `/my-work`. Expect Hello, the role Creative Director, Today saying nothing is assigned, Do this opening the content library, and no performance number. Sign in as the F&B lead and expect Uma Blu today, with no finance notes and no content library. The closer and the external accountant have no live person to sign in until someone is assigned to `POS-BZG-CLOSER-UMA-1` and `POS-GGV-EXT-ACCT`. Sign in as Owner and expect the pulse lines, Money or control at risk saying nothing is flagged, and no performance number.

## FOUNDER DEPENDENCY

- Daily list for a seated role: ELIMINATE. The page follows the role and the assignment.
- Payment, bank changes, and governance authority: RETAIN.
- Empty Wolf Core records and the missing performance figure: RETAIN. Someone has to enter real work and a real target. The page will not fill them.
- Seating a closer and an external accountant: RETAIN. Those positions exist and are empty.
- Choosing Misa's primary assignment: RETAIN. My Work follows the primary role. This pack does not move it.
- Owner picture: RETAIN.

RESULT: PASS
