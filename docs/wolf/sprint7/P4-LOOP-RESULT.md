# P4 — My Work → approval → evidence → outcome — 27 Sep 2026

Decision served: 2026-09-24 People Are Not Roles, on the existing Wolf Core governance spine. Not a new task or approval database.

ENGINEERING PASS. Not staff ready. Not human commissioned.

Production `:8787` stayed on pid 15975 (`serve.py`). Beta `:8788` was restarted with `launchctl kickstart -k` on `net.wolfcommand.serve-beta` only. It came back as pid 2734, `scripts/serve_beta.py`. No money, bank, or payment action. No NAS write. No external send.

## BEFORE

Pack 3's My Work page listed Wolf Core rows as plain text. Opening one, attaching evidence, and submitting it for a decision were not on that page.

- Work items, approvals, evidence, SoD, delegation, exceptions, and audit already existed as separate engines. Completing a linked work item did not record an approval, and approving did not complete the work item.
- There was no route that assigned a work item by role and scope, blocked submit on missing evidence, or wrote the decision back onto the same work item.
- Catalog counts taken before the scenario run: `org_authority_limits` 0, active `core_sod_constraints` 0, active `core_evidence_requirements` 1 (the Habitat content-publish requirement on `SCOPE-GGV-CONTENT`). That requirement was not changed.

## BUILT-REPAIRED

- `scripts/core/work_loop.py` orchestrates the existing engines. It does not add a table.
- Create assigns the current holder of a role and scope. The person's name is not an input. A replacement on that role inherits the queue when the previous assignment has ended. A second person who merely shares the role does not see work whose assignment is still active.
- Submit evaluates `work.loop.submit`. Missing evidence returns `missing_required_evidence` and does not create an approval. A satisfied gate creates one `core_approval_requests` row linked to the existing work item (`source_type` `WORK_ITEM`) and moves the work item to `BLOCKED`.
- Decide calls the existing approve/reject path, which already checks authority, delegation, and SoD, and writes the audit. Approve then moves the same work item to `COMPLETED`. Reject moves it back to `IN_PROGRESS`. A SoD denial on an exceptionable constraint requests a `core_governance_exceptions` row in `REQUESTED`. It is not authorised.
- My Work items that have a work item link open `/my-work/item/<id>`. The same status is read onto the worker's My Work sections, the approver's attention list, the owner pulse, and `GET /api/progress/governance-loop`. That progress slice is read from `core_work_items` at request time and labelled `LIVE`. If the read fails, the Progress page shows `STALE`. An approved request whose work item is not completed is also marked `STALE`.
- Money, bank, proven, and production routes on this loop return 405.
- `staff_ready` and `human_commissioned` stay false.

## VERIFIED

```
python3 scripts/tests/test_work_loop.py | tail -3
PASS  prod listener unchanged at end
PASS=52 FAIL=0
EXIT: SUCCESS
```

The Beta handler on an ephemeral port, with a development subject header, covered: ordinary approval (native basis, done on My Work, owner pulse, and the live progress slice, audit rows present); missing evidence blocking submit with no approval row; authority denied on a 100 IDR spend against a 10 IDR limit, item not completed; delegated `approval.decide` recorded as `DELEGATION`; SoD `sod_same_person_conflict` with an exception left `REQUESTED`; reject returning the item to today; a replacement approver inheriting the pending queue; a replacement worker inheriting the open queue after the previous assignment ended. Headless Chrome at 390px and 1280px opened the completed item and the sideways-scroll marker stayed `no`. Pack 3's staff-home test still passes (`PASS=89 FAIL=0`).

Temporary authority limit, SoD constraint, and evidence requirement were removed. Counts after cleanup match the start: limits 0, active SoD constraints 0, active evidence requirements 1. Test work items 0. Pending `P4-TEST` approvals 0. `PERS-P4-*` people 0.

Append-only leftovers, tagged and not shown as open work: 2 evidence rows set `INVALIDATED` with reason `P4-TEST cleanup`, 6 approval decisions whose requests were removed, and the `work_note` evidence type those rows reference.

Live Beta after the restart, unsigned:

```
curl -sS -D - http://127.0.0.1:8788/api/work-loop/items/none
HTTP/1.0 403 Forbidden
{"ok": false, "error": "forbidden", "message": "Sign in required.", "staff_ready": false, "human_commissioned": false}

curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8788/my-work/item/none
403

curl -sS -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8788/api/work-loop/money
405

curl -sS -D - http://127.0.0.1:8788/api/progress/governance-loop
HTTP/1.0 403 Forbidden
{"ok": false, "error": "missing_auth", "message": "Cf-Access-Jwt-Assertion required. Local :8788 without Cloudflare JWT is denied (fail-closed).", ...}
```

Listeners after the restart:

```
Python 15975 127.0.0.1:8787
Python 2734  127.0.0.1:8788  scripts/serve_beta.py
```

`scripts/serve_beta.py` and `dashboards/progress.html` already held a large unrelated uncommitted diff, so those two files were left unstaged. The loop routes and the Progress panel are in that working tree and on the restarted Beta process.

## STAFF READY?

NO.

The loop is proven with tagged seats that were removed. A person opening My Work tonight still has an empty day. Shell Home was not switched. Cloudflare sign-in on `:8788` was not done. Authorising the SoD exception is still a separate owner step, and this pack does not take it.

## HUMAN COMMISSIONED?

NO

## BLOCKERS

- BLOCKER: Wolf Core still has no real open work, pending approval, or requested exception after the test rows were closed. The pages stay empty until a real item is created.
- BLOCKER: `:8788` role screens need a Cloudflare sign-in. Development subject headers are ignored there.
- BLOCKER: authorising or rejecting a governance exception is still gated to the owner person in the existing exception engine. This pack requests the exception and stops.
- BLOCKER: the SoD exception is attached to the newest active constraint on that entity for `approval.decide`. After cleanup there is no active constraint. A second live constraint would need a tighter link than "newest".
- Remaining append-only `P4-TEST` decisions and two invalidated evidence rows are not open work. They were not hard-deleted because those tables refuse delete.

## NEXT HUMAN TEST

1. Sign in on Beta `:8788` as a person who holds the role the work was assigned to. Open `/my-work`. The item should be in "What do I need to do today?"
2. Open it. If evidence is required, submit before attaching a note and expect the block. Attach the note, submit, and expect the item to leave today and show as waiting.
3. Sign in as the role that holds `approval.decide` for that request. The same item should be under "What needs my attention?" Approve it. The worker's completed list, the owner pulse "What improved", and Progress "Work outcomes" should show it done, with Progress marked LIVE.
4. Reject a second item. It should return to the worker's today list.
5. End the worker's assignment and seat a replacement on the same role and scopes. The open item should appear for the replacement without being reassigned by name.

## FOUNDER DEPENDENCY

- Role queue: ELIMINATE. The holder of the role and scope sees the work. A replacement inherits it when the previous assignment has ended. Matt is not a routing step.
- Evidence gate and approval route: AUTOMATE. Submit and routing follow the existing engines.
- Delegated decision: ELIMINATE. Once a delegation exists, the delegate decides. Creating a delegation still requires whoever already holds `delegation.create`.
- Exception authorise: RETAIN. A SoD block can request an exception. Authorising it stays with the owner. This pack does not authorise one to get a green check.
- Payment and bank changes: RETAIN. Those routes are refused.

RESULT: PASS
