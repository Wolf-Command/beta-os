# P0 CAP-CORE-10 — Exception / Override Governance — 27 Sep 2026

Pack S2. Beta/local only. This shows the existing Owner Command exception read. It does not start a new system. Production `:8787` stayed pid 15975 (`serve.py`). Beta `:8788` was restarted from pid 76910 to pid 78725 (`scripts/serve_beta.py`) so the read loaded. No money, bank, payment, ESB, or NAS write. No exception row inserted. The no-delete trigger was not dropped. No JWT minted. No Access include changed. No push. Grok was not called.

TECHNICAL PROOF is `scripts/tests/test_cap_core_10_read.py`. DEPLOYED ROUTE PROOF is the unsigned, spoofed, and bad-JWT deny on pid 78725, and the public Access login redirect. A seated allow was not observed, so `DEPLOYED-ROUTE-PROOF-20260927` stays FAIL for that reason. STAFF READINESS stays no. HUMAN COMMISSIONING stays no. OPERATING ADOPTION stays not measured. SYSTEM stays 19.65 / 77 = 25.52%.

The row was taken because the open items ahead of it cannot be advanced by this queue. CAP-MSC-02 still needs a review note that is not this queue. CAP-CORE-01 and CAP-CORE-06 still need a real Cloudflare session. CAP-CORE-03 and CAP-CORE-04 close on that same session, and their queue prerequisites are not final. CAP-CORE-05 is already CLOSED. CAP-CORE-07 stays OPEN because its seated read was not observed. CAP-CORE-08 is BLOCKED_OWNER. CAP-CORE-09 stays OPEN because the live evidence count is 4, not 3. The queue lists CAP-CORE-09 as a prerequisite. The critical path records no extra prerequisite. This slice does not use the evidence gate list.

## BEFORE

SYSTEM PROVEN (0.80). The queue said live `core_governance_exceptions` was 2. Owner Command listed only `REQUESTED` and `AUTHORISED`. When that list was empty it said no governance exceptions were on record. `CR-f9aee8803a25b5ee` was OPEN. An operating review cadence was the READY bar.

## AFTER

The queue row stays OPEN. The ledger stays PROVEN.

The live table has 3 rows, not 2. No fourth row was inserted.

| exception_id | entity | status |
| --- | --- | --- |
| `GEX-a8165674-68a6-4033-ab5b-d310d7ded0cd` | `ENT-GGV` | `REJECTED` |
| `GEX-0973743f-c838-4545-92c5-25fea51f21c8` | `ENT-GGV` | `REJECTED` |
| `GEX-41967006-311f-4ab0-9802-1e6db54ce18e` | `ENT-GGV` | `REJECTED` |

The third row was created at `2026-09-27T10:06:44Z`, the same timestamp as the invalidated evidence residue from `scripts/tests/test_work_loop.py`. `trg_core_governance_exceptions_no_delete` remains. It was not dropped.

Owner Command now lists those stored rows for the company entities. `stored_count` is 3. `open_count` is 0, which is the `REQUESTED` or `AUTHORISED` count. The GGV card count is 3. AMG and BZG are 0. Needs you does not list the rejected rows. `cadence_done` is false. An email string and the display name `Matt` are not an allow. The allow check is `person_id` `PERS-MATT`.

On pid 78725:

| caller | `GET /api/owner/command` | `GET /wolf` |
| --- | --- | --- |
| no header | 403 `forbidden` | 403 `missing_auth` |
| spoofed email | 403 `forbidden` | 403 `missing_auth` |
| `X-Wolf-Subject: PERS-MATT` | 403 `forbidden` | 403 `missing_auth` |
| `Cf-Access-Jwt-Assertion: a.b.c` | 403 `forbidden` | 403 `invalid_token` |

None of those bodies is an exception list. Unsigned POST `/api/owner/command` is 403. The public hostname returns 302 to `https://wolfcommand.cloudflareaccess.com/cdn-cgi/access/login/beta.wolfcommand.net` for both GETs. `server: cloudflare`. `www-authenticate` starts `Cloudflare-Access`. The login query string was not recorded.

The nine new audit rows during the gate test are `auth.resolve` `DENIED` from `cf_access`. They are the deny probes. The exception rows did not change. Later suites also denied on the origin, so the audit count after those suites is not the gate-test count.

## EVIDENCE

Commit `b0fa859`. Test: `scripts/tests/test_cap_core_10_read.py`.

```
NOTE  beta_pid=78725 prod_pid=15975
NOTE  live_exceptions=3 live_audits=3609
NOTE  shown=GEX-41967006-311f-4ab0-9802-1e6db54ce18e,GEX-0973743f-c838-4545-92c5-25fea51f21c8,GEX-a8165674-68a6-4033-ab5b-d310d7ded0cd
NOTE  stored_count=3 open_count=0 cadence_done=False
NOTE  live_exceptions_after=3 live_audits_after=3618
SUMMARY pass=47 fail=0
EXIT: SUCCESS
```

Previously green suites, this session, exit 0:

| suite | result |
| --- | --- |
| `test_owner_command.py` | PASS=66 FAIL=0 |
| `test_real_auth_binding.py` | SUMMARY pass=51 fail=0 |
| `test_dashboard_truth.py` | PASS=62 FAIL=0 |
| `test_business_dashboard.py` | PASS=131 FAIL=0 |
| `test_msc_posture_prove.py` | PASS=151 FAIL=0 |
| `test_role_dashboard.py` | PASS=144 FAIL=0 |
| `test_completion_war_room.py` | PASS=227 FAIL=0 |
| `test_lead_spine.py` | PASS=33 FAIL=0 |
| `test_haikal_content_ux_wave1.py` | PASS=21 FAIL=0 |
| `test_cap_msc_02_live_gate.py` | SUMMARY pass=38 fail=0 |
| `test_cap_core_01_live_gate.py` | SUMMARY pass=123 fail=0 |
| `test_cap_core_09_gate_list.py` | SUMMARY pass=69 fail=0 |

`test_owner_command.py` includes a development-subject 200 on its own port. That 200 is not the Beta seated proof.

Listeners after the gate test, unchanged through the later suites:

```
Python  15975  127.0.0.1:8787  serve.py
Python  78725  127.0.0.1:8788  scripts/serve_beta.py
```

`state/model-c-baseline-assessments.json` was not edited. SHA256 `852f267a4bc71fe86f8972d077ec1c83f93a2de64735a2b2c8713488ddea3305`. `CAP-CORE-10` is still `PROVEN`. Row count 77. Score was not raised. `staff_ready` and `human_commissioned` stay false. Completion row `CR-f9aee8803a25b5ee` stays OPEN. Live `core_governance_exceptions` stayed 3.

## FINAL STATE

OPEN. The read half of the closure test passed. The count half failed: live `core_governance_exceptions` is 3, not 2. The seated half is absent. `cadence_done` is false. The ledger was not raised. Staff ready, human commissioned, and operating adoption stay unset.

READY_FOR_HUMAN is not met. There is no named external provider. Accepting the third row as the new count is not recorded as BLOCKED_OWNER in this pack, because the seated read is still absent and that absence is the CAP-CORE-02 walk.

## HUMAN NEXT

On https://beta.wolfcommand.net, sign in as Matt and open Wolf. Write down the three exception ids and their statuses. Open exceptions should be none. Stored should be the three rejected rows. Sign out. That look is not the operating cadence, and it is not commissioning. Do not mark anyone commissioned from this file.

RESULT: PASS
