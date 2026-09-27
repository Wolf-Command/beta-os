SYSTEM = 19.65 / 77 = 25.52% ; STAFF READY = 0 ; HUMAN COMMISSIONED = 0 ; OPERATING ADOPTION = NOT MEASURED

# W3-P5 — Completion war room and final gap register — 27 Sep 2026

Decision served: owner brief 27 Sep 2026, PACK 5, then the final reconciliation of the canonical 77. Extends the Day 2 ledger reconciliation (`docs/wolf/day2/D1-RECONCILE-RESULT.md`) and Wave 3 packs 1–4. Not a new task or approval database.

TECHNICAL PROOF is separate from DEPLOYED ROUTE PROOF, and both are separate from STAFF READINESS, HUMAN COMMISSIONING, and OPERATING ADOPTION.

Production `:8787` stayed on pid 15975 (`serve.py`). Beta `:8788` was restarted with `launchctl kickstart -k` on `gui/501/net.wolfcommand.serve-beta` only, from pid 33401 to pid 35844, still `scripts/serve_beta.py`. No money, bank, or payment action. No NAS write. No external call. The maturity ledger was not rewritten.

## BEFORE

`/wolf` had no finish war room. The 77 lived in `state/model-c-baseline-assessments.json` and on Progress. Commissioning for 12 rows lived in `state/completion-register/COMMISSIONING-STATE-20260927.json`. There was no single Owner screen of capability, domain, SYSTEM state, score, evidence, deployed proof, staff readiness, human commissioning, operating adoption, blocker, role, next action, dependency, effort, and priority.

The ledger before this pack, and after it, is the same file. Backup `state/model-c-baseline-assessments.backup-20260927-w3p5.json` matches sha256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`.

| state | caps | credit | subtotal |
| --- | ---: | ---: | ---: |
| ABSENT | 1 | 0.00 | 0.00 |
| SPECIFIED | 41 | 0.05 | 2.05 |
| BUILT | 20 | 0.25 | 5.00 |
| PROVEN | 12 | 0.80 | 9.60 |
| READY | 3 | 1.00 | 3.00 |
| **SUM** | **77** |  | **19.65** |

`19.65 / 77 × 100 = 25.51948…%`. Half-up to 2 decimals is **25.52%**. Progress rounds that same sum to 25.5%. That is one total, not a second score. Do not replace 25.52% with the reaudit figure 16.88%.

## BUILT

- `scripts/core/completion_war_room.py` is a read model. It does not add a table and it does not write the ledger. It reads the canonical ledger, the catalog, the Day 2 commissioning file, and `DEPLOYED-ROUTE-PROOF-20260927.json`.
- Priority rule `W3-P5-PRIORITY-v1` is a closed first-match on CAP-ID. It does not read the maturity state. P0 is the control kernel CAP-CORE-01 through CAP-CORE-10, plus CAP-MSC-02 and CAP-INTG-07. P1 is the founder machinery, the GGV/AMG/BZG daily loops, the minimum money picture, and the connectors those loops name. P2 follows initial commissioning, including sale readiness. P3 is brand social performance, service-improvement capture, and review capture. Counts: P0 12, P1 20, P2 42, P3 3.
- Groups, one capability each: must finish 28, must commission 3 (CAP-CORE-02, CAP-BZG-03, CAP-GGV-02), waiting on an external system 1 (CAP-INTG-01, ABSENT), follow after launch 45. Human acts already on record are listed separately and are not a score.
- Routes, Owner only: `GET /api/owner/war-room`, page `/finish-war-room`. POST, PUT, and PATCH return 403 unsigned and 405 for the Owner. Direct HTML paths unsigned are 403. `/wolf` links to the war room.
- `staff_ready`, `human_commissioned`, and `operating_adoption` stay false / false / NOT MEASURED on every row. Staff ready count 0. Human commissioned count 0.
- Reconciliation raised nothing. Candidates refused, with reasons, are in `state/completion-register/RECONCILE-W3-P5-20260927.json`: CAP-STRAT-02 stays BUILT, CAP-INTEL-02/03/04 stay PROVEN, CAP-INTG-06 stays SPECIFIED. Wave 3 desks are not a red-team and not a Cloudflare deployed-route pass.
- Commissioning for all 77: `state/completion-register/COMMISSIONING-STATE-20260927-w3p5.json`. Gap projection: `state/completion-register/GAP-REGISTER-20260927.json`.
- Lists: `docs/wolf/wave3/WHAT-IS-LEFT-TO-FINISH-WOLF-COMMAND.md` and `docs/wolf/wave3/SIX-DAY-CRITICAL-PATH.md`.

`scripts/serve_beta.py` already held a large uncommitted rebuild. The war room routes and the Owner Command link are in that working tree, which pid 35844 is running. They are not in the pack commit, so a checkout of the commit alone does not contain the route.

## VERIFIED

```
PYTHONPATH=scripts python3 scripts/tests/test_completion_war_room.py | tail -3
PASS  staff-denied shows permission-denied
PASS=227 FAIL=0
EXIT: SUCCESS
```

The first run was already PASS=227 FAIL=0. No repair pass.

Headless Chrome on the ephemeral handler: Owner `/finish-war-room` at 1280px (the 19.65 / 77 = 25.52% line, STAFF READY, NOT MEASURED, CAP-CORE-01, ready flag, no horizontal overflow) and at 390px (CAP-INTG-01, P0, NOT MEASURED, no horizontal overflow). Devi on `/finish-war-room` showed `permission-denied`. Unsigned and the other staff seats are 403 on the API and on the direct HTML paths. Owner writes are 405. The ledger hash was the same after the model read and after the HTTP run.

Previously green suites, re-run in this session, all exit 0:

```
test_owner_command.py                 PASS=66 FAIL=0
test_business_dashboard.py            PASS=131 FAIL=0
test_role_dashboard.py                PASS=144 FAIL=0
test_dashboard_truth_provenance.py    PASS=98 FAIL=0
test_dashboard_truth.py               PASS=62 FAIL=0
test_owner_empire_pack.py             PASS=80 FAIL=0
test_staff_home.py                    PASS=89 FAIL=0
test_wolf_bzg_uma_nav.py              PASS=111 FAIL=0
test_ggv_ops_pack.py                  PASS=97 FAIL=0
test_uma_daily_loop_finish.py         PASS=47 FAIL=0
```

`test_amg_ops_pack.py` was already red in Pack 4 for a live roster fact (Misa on `ROLE-AMG-GM`). This pack does not change AMG seats, so that suite was not re-run.

Deployed on Beta `:8788` after the restart to pid 35844, unsigned:

```
GET  /finish-war-room                      403  permission-denied
GET  /finish-war-room.html                 403  permission-denied
GET  /dashboards/finish-war-room.html      403  permission-denied
GET  /api/owner/war-room                   403  permission-denied
POST /api/owner/war-room                   403  permission-denied
PUT  /api/owner/war-room                   403  permission-denied
PATCH /api/owner/war-room                  403  permission-denied
```

Owner 200 was proven on the ephemeral handler with a development subject, not by bypassing the live Cloudflare gate. Production pid 15975 was still `serve.py` on `:8787` after the Beta restart. Beta pid 35844 is `scripts/serve_beta.py`.

## STAFF READY?

NO. Count is 0. A rendered Owner screen is not a staff walk.

## HUMAN COMMISSIONED?

NO. Count is 0.

## BLOCKERS

- No human evidence that Matt has opened this screen, or that any source is commissioned.
- Deployed-route proof for the 77 is still the Day 2 FAIL. Unsigned Beta is fail-closed. That does not lower the three READY rows, and it does not raise the PROVEN rows.
- CAP-INTG-01 is ABSENT. Yanolja has no reader. Occupancy was not invented.
- Finance books were not opened. UNAVAILABLE is not cash.
- CAP-INTG-07 remains SPECIFIED. The 2026-09-18 owner audit rejected treating repository checks as PROVEN. This pack did not add a vault prove.
- The closer position and the external accountant position are still empty. Variance policy count on the Day 2 register is 0. No policy was invented.
- The HTTP route and the `/wolf` link are running from the dirty working tree. Those two files were not committed, because they already contained the rest of the rebuild.

## NEXT HUMAN TEST

Sign in on Beta as Owner. Open `/wolf`, then Finish war room. Confirm the first line reads `19.65 / 77 = 25.52%`, staff ready 0, human commissioned 0, and operating adoption NOT MEASURED. Confirm CAP-INTG-01 says ABSENT and does not show an occupancy number. Confirm CAP-CORE-02, CAP-BZG-03, and CAP-GGV-02 are READY and still not commissioned. Open one P2 row and confirm it is in the follow-after list, not marked finished.

## FOUNDER DEPENDENCY

RETAIN. Declaring a source commissioned, opening the books, seating a closer and an accountant, choosing a primary assignment, and the Cloudflare sign-in stay with the Owner. This pack does not remove them. The war room shows the classes. It does not measure a reduction.

RESULT: PASS
