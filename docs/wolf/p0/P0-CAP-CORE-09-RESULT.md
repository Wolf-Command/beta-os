# P0 CAP-CORE-09 — Evidence Requirements — 27 Sep 2026

Pack S2. Beta/local only. This lists the existing Wolf Core evidence gate. It does not start a new system. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 64196 (`scripts/serve_beta.py`). No restart. No money, bank, payment, ESB, or NAS write. No evidence requirement inserted. No evidence row inserted by this inventory. The no-delete triggers were not dropped. No JWT minted. No Access include changed. No push. Grok was not called.

TECHNICAL PROOF is the gate list in `scripts/tests/test_cap_core_09_gate_list.py`. DEPLOYED ROUTE PROOF was not added: there is no new evidence HTTP route. A seated read was not observed, so `DEPLOYED-ROUTE-PROOF-20260927` stays FAIL for that reason. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

The row was taken because the open items ahead of it cannot be advanced by this queue. CAP-MSC-02 still needs a review note that is not this queue. CAP-CORE-01 and CAP-CORE-06 still need a real Cloudflare session. CAP-CORE-03 and CAP-CORE-04 close on that same session, and their queue prerequisites are not final. CAP-CORE-05 is already CLOSED. CAP-CORE-07 stays OPEN because its seated read was not observed. CAP-CORE-08 is BLOCKED_OWNER. The queue lists CAP-CORE-07 as a prerequisite. The critical path records no extra prerequisite. This list does not use the approval seated read.

## BEFORE

SYSTEM PROVEN (0.80). Live `core_evidence_records` was 3. Live `core_evidence_requirements` was 1, id `EVR-HABITAT-CONTENT-PUBLISH`, action `HABITAT.CONTENT.PUBLISH`. Live `core_approval_decisions` was 6. `CR-e594ea7dc79599e7` was OPEN. Universal evidence packs were the READY bar. The three stored records were not that list.

## AFTER

The queue row stays OPEN. The ledger stays PROVEN.

Gated, from the current functions:

| action | where | what the code does |
| --- | --- | --- |
| `approval.request` | `create_approval_request` | calls `_enforce_evidence_gate` |
| `approval.decide` | `_decide` on APPROVED | calls `_enforce_evidence_gate` |
| `work.loop.submit` | `submit_item` | denies `missing_required_evidence` when the evaluator is not satisfied |
| `HABITAT.CONTENT.PUBLISH` | `assert_habitat_publish_allowed` | requires result `SATISFIED` |
| `HABITAT.CONTENT.PUBLISH.submit` | `submit_for_approval` | `enforce_evidence=True` and `bind_policy=True` |
| `SPEND_APPROVE` | `REQUEST_TYPE_TO_ACTION` | used when a bound approval request type is `SPEND` |
| `EXCEPTION` | `REQUEST_TYPE_TO_ACTION` | used when a bound approval request type is `EXCEPTION` |
| `GENERAL_MATERIAL` | `REQUEST_TYPE_TO_ACTION` | used when a bound approval request type is `GENERAL` |

Not gated. These stay open:

| action | where | what the code does |
| --- | --- | --- |
| `venue.close.declare_cash` | `attach_declared_cash` | submits evidence and does not evaluate requirements |
| `venue.close.resolve_exception` | `resolve_exception` | submits evidence and does not evaluate requirements |
| `venue.close.verify` | `verify_close` | checks SoD and does not evaluate requirements |
| `ggv.nota.submit` | `submit_nota` | `enforce_evidence=False`, and the nota row is still updated if approval creation fails |
| `uma.receive_goods` | `receive_goods` | `require_evidence` defaults false. It submits a record and does not evaluate requirements |
| `work.item.complete` | `decide_item` | moves to `COMPLETED` and does not call `evaluate_evidence_requirements` |

The only ACTIVE requirement is still `EVR-HABITAT-CONTENT-PUBLISH`. No second requirement was inserted. Zero matching requirements still pass the approval and work-loop paths. Habitat publish still requires `SATISFIED`. That one requirement is not a universal pack.

`scripts/tests/test_work_loop.py` was re-run because it was previously green. It writes the live catalog. Its cleanup invalidates evidence and cannot delete it. After that run, live `core_evidence_records` is 4. The new row is `EVD-50e827bd-2a51-4ed2-8e3b-4e88a1fff153`, status `INVALIDATED`, reason `P4-TEST cleanup`, at `2026-09-27T10:06:44Z`. The earlier three ids remain. Live `core_approval_decisions` is 9. The three new ids are `APD-94bacc16-d184-4f8f-86d5-b46cb246791f`, `APD-0208eeb0-2d4a-453a-8946-32cfcd44ed46`, and `APD-1b7a9d12-8ff3-4159-b054-dd79318e8a02`. Those tables refuse hard delete. The triggers were not dropped.

The inventory test, run after that residue, does not change the count. `CR-e594ea7dc79599e7` stays OPEN. The ledger was not edited.

## EVIDENCE

Commit `9d0b83c`. Test: `scripts/tests/test_cap_core_09_gate_list.py`.

Before `test_work_loop.py`:

```
NOTE  live_evidence_records=3 live_requirements=1 active=[('EVR-HABITAT-CONTENT-PUBLISH', 'HABITAT.CONTENT.PUBLISH', 'ACTIVE')]
SUMMARY pass=63 fail=0
EXIT: SUCCESS
```

After `test_work_loop.py`, the same test:

```
NOTE  gated=approval.request,approval.decide,work.loop.submit,HABITAT.CONTENT.PUBLISH,HABITAT.CONTENT.PUBLISH.submit,SPEND_APPROVE,EXCEPTION,GENERAL_MATERIAL
NOTE  not_gated=venue.close.declare_cash,venue.close.resolve_exception,venue.close.verify,ggv.nota.submit,uma.receive_goods,work.item.complete
SUMMARY pass=69 fail=0
EXIT: SUCCESS
```

`test_evidence_requirements.py` this session: exit 1, pass=65 fail=8. The live-count guards now print 4, not 3. D1 already recorded that suite as red against a count of 3. Those fails were not repaired.

Previously green suites, this session, exit 0:

| suite | result |
| --- | --- |
| `test_real_auth_binding.py` | PASS=51 FAIL=0 |
| `test_msc_posture_prove.py` | PASS=151 FAIL=0 |
| `test_dashboard_truth.py` | PASS=62 FAIL=0 |
| `test_owner_command.py` | PASS=66 FAIL=0 |
| `test_business_dashboard.py` | PASS=131 FAIL=0 |
| `test_role_dashboard.py` | PASS=144 FAIL=0 |
| `test_completion_war_room.py` | PASS=227 FAIL=0 |
| `test_lead_spine.py` | PASS=33 FAIL=0 |
| `test_haikal_content_ux_wave1.py` | PASS=21 FAIL=0 |
| `test_cap_msc_02_live_gate.py` | SUMMARY pass=38 fail=0 |
| `test_cap_core_01_live_gate.py` | SUMMARY pass=123 fail=0 |
| `test_cap_core_06_trail.py` | SUMMARY pass=48 fail=0 |
| `test_cap_core_05_empty_deny.py` | SUMMARY pass=39 fail=0 |
| `test_cap_core_07_route.py` | SUMMARY pass=56 fail=0 |
| `test_cap_core_08_self_close.py` | SUMMARY pass=73 fail=0 |
| `test_work_loop.py` | PASS=52 FAIL=0 |

`test_work_loop.py` is the suite that left the invalidated row and the three decisions. It was not run again after that.

Listeners after the suites, unchanged:

```
Python  15975  127.0.0.1:8787  serve.py
Python  64196  127.0.0.1:8788  scripts/serve_beta.py
```

`state/model-c-baseline-assessments.json` was not edited. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-CORE-09` is still `PROVEN`. Row count 77. Score was not raised. `staff_ready` and `human_commissioned` stay false. Completion row `CR-e594ea7dc79599e7` stays OPEN.

No evidence route was added, so there was no new unsigned URL to check. Beta was not restarted.

## FINAL STATE

OPEN. The list half of the closure test passed. The count half failed: live `core_evidence_records` is 4, not 3. Ungated actions stay listed as not gated. The ledger was not raised. Staff ready, human commissioned, and operating adoption stay unset.

## HUMAN NEXT

None for this list. Do not drop the no-delete trigger to remove `EVD-50e827bd`. Do not treat the six open actions as gated. A universal evidence pack was not authored.

RESULT: FAIL
