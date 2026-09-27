# F2 — Machine-verifiable core P0 — 28 Sep 2026

Pack F2 of the five-pack sprint. Owner brief 28 Sep 2026 06:46 WITA, item 2. Extends Wolf Core. This is not a new system. Beta/local only. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` was restarted from pid 17892 to pid 22379 (`scripts/serve_beta.py`) because that process had started at 06:46, before the F1 classification modules were saved. It came back on `:8788`. No money, bank, payment, ESB, or NAS write. No row deleted. No no-delete trigger dropped. No policy row inserted. No grant added. No person created. No JWT minted. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_core_f2_machine.py` run through `scripts/tests/run_guarded.py`, plus the previously green core suites below. The lifecycle, classification, and dashboard movement were on a temp copy under `state/build-factory/tmp-f1/`. That copy was removed. DEPLOYED ROUTE PROOF is the unsigned, spoofed, subject-header, and bad-JWT deny on pid 22379, the sign-out redirect, and the public Access login redirect. A seated 200 was not observed. In-process 200s inside `test_real_auth_binding.py`, `test_owner_command.py`, and `test_business_dashboard.py` are that test handler. They are not a Cloudflare session on pid 22379. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

The human session is `docs/wolf/five/ONE-WALK.md`. The queue is `docs/wolf/p0/P0-QUEUE.json`.

## What the machine half proved

On the isolated copy, using person id and assignment, not a display name:

| check | result |
| --- | --- |
| Haikal active assignment | `ASG-HAIKAL-CD-1` only. `ASG-HAIKAL-VE-1` is ENDED |
| Haikal `organisation.entity.read` and `organisation.role.read` | denied. `content.plan.read` allowed. `venue.close.read` on Uma denied |
| Devi `venue.close.read` on Uma | allowed. Organisation, content, and finance reads denied |
| Matt organisation reads | allowed |
| Display name and an email string | not an allow |
| Work item | OPEN, IN_PROGRESS, BLOCKED, IN_PROGRESS, COMPLETED, VERIFIED. Verify from OPEN stayed OPEN |
| Dashboard | the work-item snapshot digest changed. The work list grew by one. `ledger_write` stayed false |
| Approval | PENDING, then APPROVED by `PERS-MATT` on `ASG-MATT-OWNER-1`. A second request went REJECTED. Devi was denied. A display name was denied. The owner card went 0 to 1 to 0 |
| Evidence | a fresh HUMAN `work_note` was valid operational and the owner valid count rose by one. After invalidate it was INVALID/TEST and the valid count returned. A `source_type` TEST row was INVALID/TEST while stored |
| Exception | a request against unregistered `EVR-HABITAT-CONTENT-PUBLISH` was `not_exceptionable`. The table did not grow. Valid operational stayed 0. INVALID/TEST stayed 3. The third id stayed listed. `cadence_done` stayed false |
| Preserved `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153` | still classified invalid |

Live catalog after the suite and after the re-runs: evidence 4, exceptions 3, approval decisions 9, approval requests 0, work items 0, policies 1, persons 6, assignments 10. The preserved row is still `INVALIDATED`, reason `P4-TEST cleanup`.

## Deployed Beta pid 22379

Unsigned, a spoofed email, `X-Wolf-Subject`, and `Cf-Access-Jwt-Assertion: a.b.c` are 403 on the entity, role, assignment, permission, work-item, approval, and owner-command routes, and on `/content-2.0`, `/bzg/uma-blu`, `/wolf`, and `/ggv/finance`. The bad JWT on `/api/owner/command` returns `forbidden`, not `invalid_token`. It is still 403 and it returns no catalog body. That was the one repair: the assertion was tightened to the denial this route already returns. `GET /signout` is 302 to the Access application logout. `GET /api/core/auth-mode` is 200, `auth_mode=cloudflare_access`. The audience value was not printed. Unsigned POST of a title to `/api/core/work-items` and `/api/core/approvals` is 403. The live counts stayed 0.

On `https://beta.wolfcommand.net`, `/api/core/me`, `/api/core/entities`, `/api/core/work-items`, `/api/core/approvals`, `/api/owner/command`, and `/wolf` return 302 to the Access login.

## Queue

| id | machine half | status now | still required |
| --- | --- | --- | --- |
| CAP-CORE-02 | complete | READY_FOR_HUMAN | the walk |
| CAP-CORE-01 | complete | READY_FOR_HUMAN | seated allow and deny |
| CAP-CORE-03 | complete | READY_FOR_HUMAN | seated assignment read |
| CAP-CORE-04 | complete | READY_FOR_HUMAN | seated route statuses |
| CAP-CORE-06 | complete | READY_FOR_HUMAN | seated read of the empty live list |
| CAP-CORE-07 | complete | BLOCKED_OWNER | a wide policy Matt authors, or a record that none is authorised. The walk still records the empty request list. No policy row was inserted |
| CAP-CORE-09 | classification complete | OPEN | six actions stay not gated. No requirement was inserted. Valid operational evidence is 0. INVALID/TEST is 4 |
| CAP-CORE-10 | complete | READY_FOR_HUMAN | the seated exception read. Cadence is not done |

CAP-CORE-05 stays CLOSED. CAP-CORE-08 and CAP-INTG-07 stay BLOCKED_OWNER. CAP-MSC-02 stays OPEN. Counts: OPEN 2, CLOSED 1, READY_FOR_HUMAN 6, BLOCKED_OWNER 3, WAITING_EXTERNAL 0.

## Suites

One repair, then the re-run. All through `scripts/tests/run_guarded.py`.

| suite | result |
| --- | --- |
| `test_cap_core_f2_machine.py` | first run SUMMARY pass=150 fail=1. After the owner-command JWT assertion: SUMMARY pass=151 fail=0 |
| `test_canonical_guard.py` | PASS=20 FAIL=0 |
| `test_real_auth_binding.py` | SUMMARY pass=51 fail=0 |
| `test_owner_command.py` | PASS=66 FAIL=0 |
| `test_business_dashboard.py` | PASS=131 FAIL=0 |
| `test_cap_core_01_live_gate.py` | SUMMARY pass=123 fail=0 |
| `test_cap_core_03_live_gate.py` | SUMMARY pass=172 fail=0 |
| `test_cap_core_04_live_gate.py` | SUMMARY pass=116 fail=0 |
| `test_cap_core_06_trail.py` | SUMMARY pass=48 fail=0. Live work items stayed 0. That suite's deny checks moved `core_audit_events` from 3993 to 4002. Work-item-source audits stayed 66 |
| `test_cap_core_07_route.py` | SUMMARY pass=56 fail=0. Live requests stayed 0. Live decisions stayed 9. Policies stayed 1 |
| `test_cap_core_09_gate_list.py` | SUMMARY pass=69 fail=0. Gated and not-gated lists unchanged. Live evidence stayed 4 |
| `test_cap_core_10_read.py` | SUMMARY pass=49 fail=0. Live exceptions stayed 3. That suite's deny checks moved `core_audit_events` from 4011 to 4020 |

Those audit rows are denied-auth records from the live gate curls. They were not deleted. They are not work items, approval requests, or evidence.

Listeners after the suites: pid 15975 is still `serve.py` on `:8787`. pid 22379 is still `scripts/serve_beta.py` on `:8788`.

RESULT: PASS
