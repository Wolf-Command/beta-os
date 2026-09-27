# W3-P1 — Owner Command Centre (/wolf) — 27 Sep 2026

Decision served: owner brief 27 Sep 2026, PACK 1. Extends the Owner Empire desk and the Pack 4 truth layer (`docs/wolf/wave3/W3-P4-TRUTH-RESULT.md`). Not a new task or approval database.

TECHNICAL PROOF is separate from DEPLOYED ROUTE PROOF, and both are separate from STAFF READINESS, HUMAN COMMISSIONING, and OPERATING ADOPTION.

Production `:8787` stayed on pid 15975 (`serve.py`). Beta `:8788` was restarted with `launchctl kickstart -k` on `net.wolfcommand.serve-beta` only, from pid 26115 to pid 28100, still `scripts/serve_beta.py`. No money, bank, or payment action. No NAS write. No external call. No ledger write.

## BEFORE

`/wolf` was the Owner Empire ledger desk: Progress SYSTEM%, Radar prove, 12-Week Year prove, and three pack handoff counts. It did not answer, on one screen, whether the businesses are okay, what changed, what is going wrong, what needs Matt, where money is at risk, what is blocked, or whether Wolf is removing him from operations. Those questions were split across My Work's owner pulse, the pack desks, and the truth register.

## BUILT

- `scripts/core/owner_command.py` is a read model. It opens the catalog read-only. It does not add a table. It reuses Wolf Core work items, approvals, governance exceptions, audit events, `org_entities`, and `org_brands`, plus the existing Empire handoffs, the staff-ops disappearance labels, the work-loop classification, and `dashboard_truth.stamp`.
- `GET /api/owner/command` is Owner only. POST, PUT, and PATCH return 403 unsigned and 405 for the Owner. Direct `/wolf` and `/owner-empire-pack` stay Owner only.
- The `/wolf` page leads with the seven questions, then group cards for GGV, AMG, and BZG, what changed, Needs you, exceptions, blocked work, and founder dependency. System health and the old ledger sit in collapsed sections. The shared `#wolfnav` shell and the Pack 4 stamp (`data-surface="empire"`) stay. Organisation brand status is a plain label. It is not painted with the truth-layer LIVE chip.
- Unknown stays UNKNOWN. Missing stays MISSING. A desk read is not a green KPI. Occupancy and cash figures are not filled in. `staff_ready`, `human_commissioned`, and `operating_adoption` are false. `less_dependent` is `NOT MEASURED`.

Read at the end of this pack, from the local catalog, not from a manufactured score:

| company | desk attention | finance | occupancy | guests | open work | blocked | approvals | exceptions | priorities |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GGV | READ 3 | UNAVAILABLE | MISSING | UNKNOWN | READ 0 | READ 0 | READ 0 | READ 0 | EMPTY |
| AMG | READ 0 | UNAVAILABLE | UNAVAILABLE | UNKNOWN | READ 0 | READ 0 | READ 0 | READ 0 | EMPTY |
| BZG | READ 0 | UNAVAILABLE | MISSING | UNKNOWN | READ 0 | READ 0 | READ 0 | READ 0 | EMPTY |

GGV 3 is the existing ops-pack attention count (leads waiting on a recorded source time). It is not a health score. AMG occupancy is UNAVAILABLE because Yanolja has no reader. Finance is UNAVAILABLE because the books were not opened. Guest issues are UNKNOWN. Zero open work is an empty read, not a claim that the business is fine.

Needs you: no pending approval and no requested exception. Seven sources still need a commissioning decision (the Pack 4 register, each `commissioned` false). That queue is not an infrastructure repair list.

What changed: 8 audit events on these companies. The newest action on record is `work.create` for GGV.

Exceptions: the governance table was read. No REQUESTED or AUTHORISED row. Empty is not unknown. Severity, current action, and escalation have no column, so those fields stay MISSING.

Founder classes on this screen: ELIMINATE 3, AUTOMATE 3, AUGMENT 1, SIMPLIFY 0, RETAIN 6. Uma ops is ELIMINATE because a staff seat can take that daily queue. Payment, bank change, exception authority, and the owner picture stay RETAIN. SIMPLIFY has no item in this classification. That is not a measured reduction.

Operating businesses under the cards come from `org_brands`. Uma Blu Brunch Cafe links to `/bzg/uma-blu`. The other brands have no separate desk on this screen.

`scripts/serve_beta.py` already held a large uncommitted rebuild (about 16k insertions against HEAD). The command route is in that working tree, which pid 28100 is running. It is not in the pack commit, so a checkout of the commit alone does not contain the route.

## VERIFIED

```
python3 scripts/tests/test_owner_command.py | tail -3
PASS  staff-denied shows permission-denied
PASS=66 FAIL=0
EXIT: SUCCESS
```

The first run of that suite was PASS=63 FAIL=3 (the question text was only in the API, and a staff `/wolf` denial did not say `permission-denied`). One repair put the seven questions in the page and added the permission-denied component on the Owner person gate. The suite was then green. A later honesty fix stopped organisation brand status from using the truth-layer LIVE chip. The suite was run again: PASS=66 FAIL=0.

Headless Chrome on the ephemeral handler: Owner `/wolf` at 1280px (the okay question, Needs you, GGV, command ready, no horizontal overflow) and at 390px (AMG, BZG, NOT MEASURED, no horizontal overflow). Devi on `/wolf` showed `permission-denied`. Unsigned and the other staff seats are 403 on the command API. Owner writes are 405. Devi is forbidden in the model.

Previously green suites, re-run in this session:

```
python3 scripts/tests/test_owner_empire_pack.py | tail -3
PASS=80 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_dashboard_truth_provenance.py | tail -3
PASS=98 FAIL=0

python3 scripts/tests/test_dashboard_truth.py | tail -3
PASS=62 FAIL=0

python3 scripts/tests/test_staff_home.py | tail -3
PASS  beta 8788 up
PASS=89 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_wolf_bzg_uma_nav.py | tail -3
PASS=111 FAIL=0
EXIT: SUCCESS

python3 scripts/tests/test_ggv_ops_pack.py | tail -3
PASS=97 FAIL=0
```

`test_amg_ops_pack.py` was already red in Pack 4 for a live roster fact (Misa on `ROLE-AMG-GM`). This pack does not change AMG seats, so that suite was not re-run.

Deployed on Beta `:8788` after the restart, unsigned:

```
/wolf                         403  missing_auth  (Cloudflare JWT required; no ui component on this anon page body)
/owner-empire-pack            403
/api/owner/command            403  forbidden  ui.component permission-denied
POST /api/owner/command       403  forbidden  ui.component permission-denied
```

Owner 200 was proven on the ephemeral handler with a development subject, not by bypassing the live Cloudflare gate. Production pid 15975 was still `serve.py` on `:8787` after the Beta restart. Beta pid 28100 is `scripts/serve_beta.py`.

## STAFF READY?

NO. `staff_ready` is false. A rendered Owner screen is not a staff walk.

## HUMAN COMMISSIONED?

NO.

## BLOCKERS

- No human evidence that Matt has used this screen, or that any source is commissioned.
- Finance books were not opened. UNAVAILABLE is not a cash position.
- Yanolja has no reader. AMG occupancy was not invented.
- Guest issues have no source. They stay UNKNOWN.
- No priorities are on the work record for these three companies.
- Founder dependency is a classification. It is not a measured reduction. `less_dependent` is NOT MEASURED.
- The HTTP route is running from the dirty `scripts/serve_beta.py` working tree. That file was not committed, because it already contained the rest of the rebuild.

## NEXT HUMAN TEST

Sign in on Beta as Owner and open `/wolf`. Read the seven answers against the table above. Confirm GGV's 3 is desk attention, not a green score. Confirm finance says UNAVAILABLE and AMG occupancy says UNAVAILABLE. Open Uma Blu from the BZG card and confirm it lands on `/bzg/uma-blu`. Open Needs you and confirm the rows are commissioning decisions, not repair tickets. Confirm "Less dependent" says NOT MEASURED.

## FOUNDER DEPENDENCY

RETAIN. The daily picture, payment, bank changes, exception authority, and declaring a source commissioned stay with the Owner. This pack does not remove them. Uma ops is labelled ELIMINATE only because a staff seat can take that queue. That label is not operating adoption.

RESULT: PASS
