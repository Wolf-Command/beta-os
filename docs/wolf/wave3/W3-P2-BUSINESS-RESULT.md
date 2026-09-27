# W3-P2 — Business dashboard system — 27 Sep 2026

Decision served: owner brief 27 Sep 2026, PACK 2. Extends Owner Command (`docs/wolf/wave3/W3-P1-OWNER-RESULT.md`) and the Pack 4 truth layer (`docs/wolf/wave3/W3-P4-TRUTH-RESULT.md`). Not a new task or approval database.

TECHNICAL PROOF is separate from DEPLOYED ROUTE PROOF, and both are separate from STAFF READINESS, HUMAN COMMISSIONING, and OPERATING ADOPTION.

Production `:8787` stayed on pid 15975 (`serve.py`). Beta `:8788` was restarted with `launchctl kickstart -k` on `net.wolfcommand.serve-beta` only, from pid 28100 to pid 31017 and then to pid 31422, still `scripts/serve_beta.py`. No money, bank, or payment action. No NAS write. No external call. No ledger write.

## BEFORE

`/wolf` opened GGV, AMG, and BZG straight into the specialist packs (`/ggv-ops-pack`, `/amg-ops-pack`, `/bzg`) and Uma Blu straight into `/bzg/uma-blu`. There was no shared business contract. Today, performance against a real target, who owns today's work, money actually available, guests, exceptions, three priorities, and recent activity were not one projection. A change in canonical state had no shared rule that every derived business desk updates or shows STALE.

## BUILT

- `scripts/core/business_dashboard.py` is a read model. It opens the catalog read-only. It does not add a table. One snapshot is the canonical state: `org_entities`, `org_brands`, `org_locations`, `org_brand_locations`, `org_departments`, `core_work_items`, `core_governance_exceptions`, `core_approval_requests`, and recent `core_audit_events`, plus the Pack 4 source stamps. Dashboards do not read past that snapshot.
- Hierarchy on every desk: WOLF/GROUP → LEGAL ENTITY → SITE → BUSINESS UNIT/VENUE → DEPARTMENT/FUNCTION → WORKSPACE → OBJECT. Empty levels say EMPTY or MISSING. They are not filled in.
- Sections on every desk: Today, Performance, People, Money, Customers / guests, Exceptions, Priorities, Recent activity.
- Routes, Owner only: `GET /api/business`, `GET /api/business/{amg|bzg|uma-blu|ggv}`, pages `/business`, `/business/amg`, `/business/bzg`, `/business/uma-blu`, `/business/ggv`. POST, PUT, and PATCH return 403 unsigned and 405 for the Owner. Direct HTML paths unsigned are 403.
- `/wolf` now drills to those desks. Uma Blu on the BZG card drills to `/business/uma-blu`. Specialist workspaces stay underneath as links: `/amg-ops-pack`, `/bzg`, `/bzg/uma-blu` (and Uma bills, issues, petty, close), `/ggv-ops-pack`, `/ggv/finance`. Their figures are not copied.
- Propagation: every desk carries the same snapshot digest. The next projection of a changed snapshot is CURRENT and shows the new value where that desk includes it. A held digest that disagrees is STALE via the Pack 4 stale path, `shown_as_current` is false, and the sections are withheld. A catalog read that fails raises, so the desk is UNAVAILABLE rather than a blank hierarchy labelled MISSING.
- `staff_ready`, `human_commissioned`, and `operating_adoption` are false. Money value is null. No green KPI.

`scripts/serve_beta.py` already held a large uncommitted rebuild (about 15k insertions against HEAD). The business routes are in that working tree, which pid 31422 is running. They are not in the pack commit, so a checkout of the commit alone does not contain the routes.

Read after the repair, from the local catalog, not from a manufactured score:

| desk | today | performance | people | money | guests | exceptions | priorities | activity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AMG / Atrium | READ open 0, blocked 0 | MISSING | EMPTY | UNAVAILABLE | UNAVAILABLE | READ 0 | EMPTY | EMPTY |
| BZG | READ open 0, blocked 0 | MISSING | EMPTY | UNAVAILABLE | UNKNOWN | READ 0 | EMPTY | EMPTY |
| Uma Blu | MISSING | MISSING | MISSING | UNAVAILABLE | UNKNOWN | MISSING | MISSING | EMPTY |
| GGV | READ open 0, blocked 0 | MISSING | EMPTY | UNAVAILABLE | UNKNOWN | READ 0 | EMPTY | READ |

Zero open work is an empty read, not a claim that the day is fine. Performance is MISSING because no target is stored. `org_scope_targets` is an access scope, not a performance target, and it was not used as one. Money is UNAVAILABLE because the books were not opened. It is not zero. AMG guests are UNAVAILABLE because Yanolja has no reader. BZG and Uma guest issues are UNKNOWN. GGV has no customer list on this desk. The ops pack was not copied into a customer count.

Uma Blu does not wear BZG totals. Work, exceptions, and priorities are stored on the legal entity, so those Uma sections stay MISSING. Uma's site is Atrium Lombok. Its venue is Uma Blu Brunch Cafe. Departments are not stored on the venue.

AMG's legal entity is Atrium Management Group. Its site and venue are Atrium Lombok. Departments on the entity are Engineering and Executive. BZG's venues on record are Catering, Merah Underground Nightclub and Bar, Blu Zone Rainforest Restaurant & Bar, Rooftop Bar - name TBD, Room Service, and Uma Blu Brunch Cafe. "name TBD" is the stored label. GGV has no site on record. Its brands are Goss Group, Selo Group, The One, Tropik, and Habitat. Its department is Content. GGV activity is READ from audit rows on the entity. The actor on those rows is not an organisation person, so the actor and the role stay MISSING.

## VERIFIED

```
python3 scripts/tests/test_business_dashboard.py | tail -3
PASS  wolf-drill shows data-command-ready="1"
PASS=131 FAIL=0
EXIT: SUCCESS
```

The first run was already PASS=131 FAIL=0. One repair then stopped a failed catalog list from coming back as missing businesses. The suite was run again: PASS=131 FAIL=0. That repair was not given a separate broken-database test. The happy path, the in-memory propagation, and the stale HTTP path were in the green run.

Propagation, in memory, no catalog write: the AMG legal name was changed on a copy of the snapshot. All four desks took the new digest and stayed CURRENT. The AMG desk showed the changed legal name. BZG, Uma Blu, and GGV did not wear that name. Holding the old digest against the new snapshot marked all four STALE, with sections withheld and `shown_as_current` false. The same stale path over HTTP, `GET /api/business?projected=not-the-canonical-state`, withheld sections on all four. A matching digest stayed CURRENT.

Headless Chrome on the ephemeral handler: Owner `/business/amg` at 1280px (AMG / Atrium, Today, Performance, Atrium Management Group, money section, no horizontal overflow) and `/business/uma-blu` at 390px (Uma Blu, Customers / guests, today section, no horizontal overflow). Owner `/business/ggv?projected=not-the-canonical-state` showed STALE, "not shown as current", and no money section. Devi on `/business/bzg` showed `permission-denied`. Owner `/wolf` at 1280px contained `/business/amg` and `/business/uma-blu`. Unsigned and the other staff seats are 403. Owner writes are 405.

Previously green suites, re-run in this session:

```
python3 scripts/tests/test_owner_command.py | tail -3
PASS=66 FAIL=0
EXIT: SUCCESS

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

Deployed on Beta `:8788` after the restart to pid 31422, unsigned:

```
/api/business          403  forbidden  ui.component permission-denied
/business/amg          403  forbidden  ui.component permission-denied
/business/uma-blu      403  forbidden  ui.component permission-denied
/business/bzg          403
/business/ggv          403
/business              403
/business-dashboard.html 403
POST /api/business     403
```

Owner 200 was proven on the ephemeral handler with a development subject, not by bypassing the live Cloudflare gate. Production pid 15975 was still `serve.py` on `:8787` after both Beta restarts. Beta pid 31422 is `scripts/serve_beta.py`.

## STAFF READY?

NO. `staff_ready` is false. A rendered Owner desk is not a staff walk.

## HUMAN COMMISSIONED?

NO.

## BLOCKERS

- No human evidence that Matt has opened these desks.
- No performance target is stored. MISSING is not a result against a plan.
- Finance books were not opened. UNAVAILABLE is not cash on hand.
- Yanolja has no reader. AMG guests were not invented.
- Guest issues on BZG and Uma have no source. They stay UNKNOWN.
- Uma's work, exceptions, and priorities are not stored on the venue, so those sections stay MISSING rather than copying BZG.
- GGV has no site on record. Its activity names an actor who is not an organisation person.
- No priorities are on the work record.
- The HTTP routes are running from the dirty `scripts/serve_beta.py` working tree. That file was not committed, because it already contained the rest of the rebuild.

## NEXT HUMAN TEST

Sign in on Beta as Owner and open `/wolf`. Open AMG and confirm the legal name is Atrium Management Group, the venue is Atrium Lombok, money says UNAVAILABLE, guests say UNAVAILABLE, and open work is 0 as an empty read. Open BZG, then Uma Blu, and confirm Uma does not repeat BZG's open-work count. Open GGV and confirm there is no site and no customer count. Open one specialist link, such as `/amg-ops-pack` or `/bzg/uma-blu`, and confirm that desk is still the workspace underneath, not a second copy of these figures.

## FOUNDER DEPENDENCY

RETAIN. Declaring a target, opening the books, commissioning Yanolja, and treating a source as current stay with the Owner. This pack does not remove them.

RESULT: PASS
