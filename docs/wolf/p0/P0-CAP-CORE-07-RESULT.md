# P0 CAP-CORE-07 — Approval Engine — 27 Sep 2026

Pack S2. Beta/local only. This uses the existing Wolf Core approval engine under the owner brief of 27 Sep 2026 16:32 WITA. It does not start a new system. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` stayed pid 64196 (`scripts/serve_beta.py`). No restart. No money, bank, payment, ESB, or NAS write. No approval request inserted. No governance policy inserted. No JWT minted. No Access include changed. No push. Grok was not called.

TECHNICAL PROOF is the copy read in `scripts/tests/test_cap_core_07_route.py`. DEPLOYED ROUTE PROOF is the unsigned, spoofed, and bad-JWT deny on pid 64196, and the public Access login redirect. A seated read was not observed, so `DEPLOYED-ROUTE-PROOF-20260927` stays FAIL for that reason. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

The row was taken because the open items ahead of it cannot be advanced by this queue. CAP-MSC-02 still needs a review note that is not this queue. CAP-CORE-01 and CAP-CORE-06 still need a real Cloudflare session. CAP-CORE-03 and CAP-CORE-04 close on that same session, and their queue prerequisites are not final. CAP-CORE-05 is already CLOSED. The queue lists CAP-CORE-06 as a prerequisite. The critical path records no extra prerequisite. This slice does not use the work-item trail.

## BEFORE

SYSTEM PROVEN (0.80). The approval engine and its tests existed. Live `core_approval_requests` count was 0. Live `core_approval_decisions` count was 6. Live `core_governance_policies` count was 1. D1 had kept the ledger at PROVEN. Wide production policy packs were the READY bar. No pack had been authored for this queue.

## AFTER

The row stays OPEN.

On a copy of the catalog, `list_approval_requests` for `PERS-MATT` returned an empty list. The person resolved `ENT-BZG` and `ENT-GGV` through assignment scope. An email string resolved no entity and returned an empty list. A display name was not the allow reason. The copy's `total_changes` did not move. The copy was deleted.

Live `core_approval_requests` stayed 0. Live `core_approval_decisions` stayed 6. Those six decisions are still stored, and each one has no matching request row. They were decided by `PERS-P4-APPROVER-2` and `PERS-P4-DELEGATE`. They were not turned into requests and they were not treated as a pack. Live `core_governance_policies` stayed 1. The stored id is `GPO-HABITAT-CONTENT-PUBLISH`, version 1, status ACTIVE, entity `ENT-GGV`, action `HABITAT.CONTENT.PUBLISH`, `created_by_person_id` `PERS-MATT`. That row was already there. This pack did not insert it. It is not a wide production policy pack.

On pid 64196, these four callers are denied on `GET /api/core/approvals` and `GET /api/core/approvals/APR-NONE`. None of them returns an approval:

| caller | status | error |
| --- | --- | --- |
| no header | 403 | `missing_auth` |
| `Cf-Access-Authenticated-User-Email: spoofed@example.invalid` | 403 | `missing_auth` |
| `X-Wolf-Subject: PERS-MATT` | 403 | `missing_auth` |
| `Cf-Access-Jwt-Assertion: a.b.c` | 403 | `invalid_token` |

Unsigned `POST /api/core/approvals` with a title was 403. The live request count stayed 0 after that POST. Live approval-source audits stayed 20. The nine new `core_audit_events` rows from these deny checks are `auth.resolve` / `DENIED` / source `cf_access`. They are not approval requests. `cf_access` moved from 1350 to 1359 on that prove. Later suites in this session wrote more of the same deny rows. Those rows were not deleted.

On `https://beta.wolfcommand.net`, those two GET paths return 302 to `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/beta.wolfcommand.net`, `server: cloudflare`, `www-authenticate` starting `Cloudflare-Access`. The login query string was not recorded.

No seated session was opened. The ledger was not edited.

## EVIDENCE

Commit `ab4af72`. Test: `scripts/tests/test_cap_core_07_route.py`.

```
WOLF_TEST_MODE=1 python3 scripts/tests/test_cap_core_07_route.py
NOTE  beta_pid=64196 prod_pid=15975
NOTE  live_requests=0 live_decisions=6 live_policies=1 live_approval_audits=20
NOTE  visible=ENT-BZG,ENT-GGV
NOTE  policy_ids=GPO-HABITAT-CONTENT-PUBLISH
NOTE  copy_requests=0 copy_decisions=6 copy_policies=1
NOTE  live_requests_after=0 live_decisions_after=6 live_policies_after=1 live_approval_audits_after=20
SUMMARY pass=56 fail=0
EXIT: SUCCESS
```

`test_approval_engine.py` this session, run alone: `pass=57 fail=3`. The three fails are `live approval decisions=0` got 6, `live approval decisions still 0` got 6, and `FINAL live approvals=0`. D1 already recorded that the live decision count is 6. They were not repaired. A green repository suite would not close this item.

`test_dual_approval.py` and `test_approval_policy_binding.py` abort with `ApprovalError: required permission denied: test.spend.approve`. D1 already recorded that abort: the fixture grants `ROLE-GGV-EDIT` and the active seat is `ROLE-GGV-CREATIVE-DIRECTOR`. They were not repaired.

A first parallel run of the previously green suites raced three of them (`test_business_dashboard.py`, `test_cap_core_01_live_gate.py`, `test_cap_core_06_trail.py`) because live audit and org counts moved while they ran. Run alone afterwards, those three exited 0. The serial results are the ones below.

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

Listeners after the suites, unchanged:

```
Python  15975  127.0.0.1:8787  serve.py
Python  64196  127.0.0.1:8788  scripts/serve_beta.py
```

`state/model-c-baseline-assessments.json` was not edited. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-CORE-07` is still `PROVEN`. Row count 77. Score was not raised. `staff_ready` and `human_commissioned` stay false. Completion row `CR-fb1af5c252e28d77` stays OPEN.

## FINAL STATE

OPEN.

The closure test has two halves, and a pack rule. The copy read lists the stored empty request table, and the live request count stayed 0. No policy row was inserted. That half exits 0. The Beta read under a real session was not observed. CLOSED is not met. READY_FOR_HUMAN is not met: the seated read is still missing, and there is no separate acceptance for a person to perform. There is no named external provider. The missing session is the CAP-CORE-02 walk, not a new owner decision, so this row is not BLOCKED_OWNER yet. After that seated status exists, the row is still not CLOSED unless Matt has authored a wide production policy pack or recorded that no pack is authorised. `GPO-HABITAT-CONTENT-PUBLISH` is not that pack. The six stored decisions are not that pack.

## HUMAN NEXT

No new one-minute walk. The sign-in already in `docs/wolf/p0/HUMAN-TESTS.md` is the session this row needs. After that session exists, record the status and count of `GET /api/core/approvals`. The stored live request list is empty. Do not create a request to fill it. Do not send `X-Wolf-Subject`. Do not mark anyone commissioned from this file. Do not treat this copy read as staff ready. Matt still has to author a wide production policy pack, or record that no pack is authorised. Cursor does not write that pack.

RESULT: PASS
